import json
import tempfile
from pathlib import Path

import fakeredis
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def app_with_fake_redis(redis_client, monkeypatch, tmp_path):
    import yaml

    import src.app as app_module

    # Patch Redis to return fake client
    def mock_redis(*args, **kwargs):
        return redis_client

    monkeypatch.setattr(app_module, "Redis", mock_redis)

    # Write temp config file
    config_data = {
        "server": {"host": "127.0.0.1", "port": 8080},
        "redis": {"host": "127.0.0.1", "port": 6379, "db": 0},
        "scheduler": {
            "timezone": "Asia/Shanghai",
            "tick_seconds": 1.0,
            "misfire_grace_seconds": 60,
        },
    }
    config_path = tmp_path / "scheduler.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)

    # Write temp job definitions
    jobs_data = {
        "jobs": [
            {
                "name": "integration_test_job",
                "cron": "0 30 16 * * 1-5",
                "stream": "cron:jobs:integration_test",
                "payload": {"job_type": "integration_test"},
                "timeout": 60,
                "max_retries": 1,
            }
        ]
    }
    job_defs_path = tmp_path / "definitions.yaml"
    with open(job_defs_path, "w", encoding="utf-8") as f:
        yaml.dump(jobs_data, f)

    from src.app import create_app

    app, _ = create_app(
        config_path=str(config_path),
        job_defs_path=str(job_defs_path),
    )
    return app


class TestHealthEndpoint:
    def test_health_returns_ok(self, app_with_fake_redis):
        client = TestClient(app_with_fake_redis)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "jobs" in data


class TestJobExecution:
    def test_manual_trigger_publishes_to_stream(self, app_with_fake_redis, redis_client):
        from src.publisher import MessagePublisher

        publisher = MessagePublisher(redis_client)

        job_def = {
            "name": "integration_test_job",
            "stream": "cron:jobs:integration_test",
            "timeout": 60,
            "max_retries": 1,
            "payload": {"job_type": "integration_test"},
        }

        msg_id = publisher.publish(job_def)
        assert msg_id is not None

        messages = redis_client.xrange("cron:jobs:integration_test", "-", "+")
        assert len(messages) == 1

        _, data = messages[0]
        assert data["job_type"] == "integration_test"
        assert data["timeout"] == "60"
        assert json.loads(data["payload"]) == {"job_type": "integration_test"}
