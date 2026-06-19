from typing import Any

from publisher import MessagePublisher


def register_jobs(cron, publisher: MessagePublisher, job_defs: list[dict[str, Any]]) -> None:
    for job_def in job_defs:
        if not job_def.get("cron"):
            continue
        _register_one(cron, publisher, job_def)


def _register_one(cron, publisher: MessagePublisher, job_def: dict[str, Any]) -> None:
    job_name = job_def["name"]
    cron_expression = job_def["cron"]

    def _fire():
        publisher.publish(job_def)

    _fire.cron_func_name = job_name  # type: ignore[attr-defined]

    cron.add_job(
        _fire,
        expression=cron_expression,
        trigger="cron",
        job_id=job_name,
        name=job_name,
    )
