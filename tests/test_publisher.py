import json
from datetime import datetime, timezone, timedelta

import pytest
from redis import Redis

from src.publisher import MessagePublisher, build_message


class TestBuildMessage:
    def test_build_message_fields(self):
        job_def = {
            "name": "fund_incremental",
            "timeout": 600,
            "max_retries": 3,
            "payload": {"job_type": "fund_incremental"},
        }
        msg = build_message(job_def)

        assert msg["job_type"] == "fund_incremental"
        assert msg["timeout"] == 600
        assert msg["max_retries"] == 3
        assert msg["payload"] == json.dumps({"job_type": "fund_incremental"})
        assert msg["job_id"].startswith("fund_incremental:")
        # ISO8601 timestamp
        datetime.fromisoformat(msg["triggered_at"])
        datetime.fromisoformat(msg["job_id"].split(":", 1)[1])

    def test_build_message_timestamps_are_utc(self):
        job_def = {
            "name": "test_job",
            "timeout": 60,
            "max_retries": 1,
            "payload": {},
        }
        before = datetime.now(timezone.utc)
        msg = build_message(job_def)
        after = datetime.now(timezone.utc)

        triggered = datetime.fromisoformat(msg["triggered_at"])
        assert before - timedelta(seconds=1) <= triggered <= after + timedelta(seconds=1)


class TestMessagePublisher:
    @pytest.fixture
    def redis_client(self):
        import fakeredis
        return fakeredis.FakeRedis()

    def test_publish_adds_message_to_stream(self, redis_client):
        publisher = MessagePublisher(redis_client)
        job_def = {
            "name": "test_job",
            "stream": "cron:jobs:test_job",
            "timeout": 60,
            "max_retries": 1,
            "payload": {"job_type": "test_job"},
        }
        msg_id = publisher.publish(job_def)

        assert msg_id is not None
        # Verify message is in the stream
        messages = redis_client.xrange("cron:jobs:test_job", "-", "+")
        assert len(messages) == 1
        stream_msg_id, stream_data = messages[0]
        # fakeredis returns bytes keys
        data = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v
                for k, v in stream_data.items()}
        assert data["job_type"] == "test_job"
