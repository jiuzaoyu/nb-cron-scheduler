import os
from contextlib import asynccontextmanager
from pathlib import Path
from zoneinfo import ZoneInfo

import uvicorn
from fastapi import FastAPI
from nb_cron import NbCron
from nb_cron.web import get_fastapi_app
from redis import Redis

from config_loader import load_job_definitions, load_scheduler_config
from job_registry import register_jobs
from publisher import MessagePublisher

ROOT = Path(__file__).resolve().parents[1]


def create_app(config_path: str | None = None, job_defs_path: str | None = None):
    config_path = config_path or str(ROOT / "config" / "scheduler.yaml")
    job_defs_path = job_defs_path or str(ROOT / "jobs" / "definitions.yaml")

    cfg = load_scheduler_config(config_path)
    job_defs = load_job_definitions(job_defs_path)

    redis_cfg = cfg["redis"]
    redis_cfg["host"] = os.getenv("REDIS_HOST", redis_cfg["host"])
    redis_cfg["port"] = int(os.getenv("REDIS_PORT", redis_cfg["port"]))
    redis_cfg["db"] = int(os.getenv("REDIS_DB", redis_cfg["db"]))

    sched_cfg = cfg["scheduler"]
    redis_password = os.getenv("REDIS_PASSWORD", None)
    redis_client = Redis(
        host=redis_cfg["host"],
        port=redis_cfg["port"],
        db=redis_cfg["db"],
        password=redis_password,
        decode_responses=True,
    )
    try:
        redis_client.ping()
    except Exception as e:
        print(f"[nb-cron] Redis 连接失败: {e}")
        raise SystemExit(1)
    publisher = MessagePublisher(redis_client)

    # 调度器名称: "nb-cron-scheduler"
    # tick_seconds:          时钟精度，每秒检查一次到期任务
    # misfire_grace_seconds: 错过补偿窗口，超时未触发的任务不再补触发
    # tz:                    时区
    cron = NbCron(
        "nb-cron-scheduler",
        tick_seconds=sched_cfg.get("tick_seconds", 1.0),
        misfire_grace_seconds=sched_cfg.get("misfire_grace_seconds", 60),
        tz=ZoneInfo(sched_cfg.get("timezone", "Asia/Shanghai")),
    )

    # cron:      调度器
    # publisher: 消息发布器，将任务消息写入 Redis Stream
    # job_defs:  job 定义列表，含 name/cron/params 等字段
    register_jobs(cron, publisher, job_defs)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        cron.start()
        yield
        cron.stop()

    app = get_fastapi_app(cron, title="nb-cron-scheduler", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok", "jobs": len(job_defs)}

    @app.post("/jobs/{job_name}/trigger")
    def trigger_job(job_name: str):
        for job_def in job_defs:
            if job_def["name"] == job_name:
                msg_id = publisher.publish(job_def)
                return {"status": "triggered", "job_name": job_name, "message_id": msg_id}
        return {"status": "not_found", "job_name": job_name}, 404

    return app, cfg


def app_factory():
    app, _ = create_app()
    return app


def main():
    app, cfg = create_app()
    server_cfg = cfg["server"]

    uvicorn.run(
        app,
        host=server_cfg["host"],
        port=server_cfg["port"],
        log_level="info",
    )


if __name__ == "__main__":
    main()
