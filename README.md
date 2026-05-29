# nb-cron-scheduler

通用定时任务调度服务 — 按 cron 表达式触发，往 Redis Streams 发布消息。

零业务逻辑。不关心谁在消费、消费结果如何。

## 快速开始

```bash
pip install -r requirements.txt
python src/app.py
```

服务启动后：
- Web UI: http://127.0.0.1:8080/nb_cron/ui/
- Health: http://127.0.0.1:8080/health

## 添加 Job

编辑 `jobs/definitions.yaml`：

```yaml
jobs:
  - name: my_job
    cron: "0 9 * * 1-5"
    stream: "cron:jobs:my_job"
    payload:
      job_type: "my_job"
    timeout: 300
    max_retries: 3
```

重启服务即生效。

## 消息格式

每次触发，向对应 Redis Stream 发送：

```json
{
  "job_id": "my_job:2026-05-29T09:00:00+00:00",
  "job_type": "my_job",
  "triggered_at": "2026-05-29T09:00:00+00:00",
  "timeout": 300,
  "max_retries": 3,
  "payload": "{\"job_type\": \"my_job\"}"
}
```

## 配置

`config/scheduler.yaml`：

```yaml
server:
  host: "127.0.0.1"
  port: 8080

redis:
  host: "127.0.0.1"
  port: 6379
  db: 0
  stream_prefix: "cron:jobs"

scheduler:
  timezone: "Asia/Shanghai"
```

## 消费者接入

业务项目作为 Redis Streams Consumer Group 消费消息：

```python
from redis import Redis

r = Redis(decode_responses=True)

# 创建 Consumer Group（幂等）
try:
    r.xgroup_create("cron:jobs:my_job", "my_group", mkstream=True)
except Exception:
    pass

# 消费循环
while True:
    messages = r.xreadgroup("my_group", "consumer_1",
                            {"cron:jobs:my_job": ">"}, block=5000, count=1)
    for stream, msgs in messages:
        for msg_id, data in msgs:
            handle_job(data)
            r.xack("cron:jobs:my_job", "my_group", msg_id)
```
