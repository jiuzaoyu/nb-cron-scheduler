import json
from datetime import datetime, timezone
from typing import Any

from redis import Redis


def build_message(job_def: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    job_name = job_def["name"]
    return {
        "job_id": f"{job_name}:{now.isoformat()}",
        "job_type": job_def.get("payload", {}).get("job_type", job_name),
        "triggered_at": now.isoformat(),
        "timeout": job_def.get("timeout", 300),
        "max_retries": job_def.get("max_retries", 0),
        "payload": json.dumps(job_def.get("payload", {})),
    }


class MessagePublisher:
    def __init__(self, redis_client: Redis):
        self._redis = redis_client

    def publish(self, job_def: dict[str, Any]) -> str:
        message = build_message(job_def)
        stream = job_def["stream"]
        msg_id = self._redis.xadd(stream, message, maxlen=10000)
        return msg_id
