import tempfile
from pathlib import Path
from src.config_loader import load_scheduler_config, load_job_definitions


def test_load_scheduler_config():
    yaml_content = """
server:
  host: "0.0.0.0"
  port: 9090
redis:
  host: "10.0.0.1"
  port: 6380
  db: 1
  stream_prefix: "test:jobs"
scheduler:
  timezone: "UTC"
  tick_seconds: 2.0
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        cfg = load_scheduler_config(tmp_path)
        assert cfg["server"]["host"] == "0.0.0.0"
        assert cfg["server"]["port"] == 9090
        assert cfg["redis"]["host"] == "10.0.0.1"
        assert cfg["redis"]["stream_prefix"] == "test:jobs"
        assert cfg["scheduler"]["timezone"] == "UTC"
    finally:
        Path(tmp_path).unlink()


def test_load_job_definitions():
    yaml_content = """
jobs:
  - name: test_job
    cron: "*/5 * * * *"
    stream: "test:jobs:demo"
    payload:
      key: value
    timeout: 60
    max_retries: 1
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        jobs = load_job_definitions(tmp_path)
        assert len(jobs) == 1
        assert jobs[0]["name"] == "test_job"
        assert jobs[0]["cron"] == "*/5 * * * *"
        assert jobs[0]["stream"] == "test:jobs:demo"
        assert jobs[0]["payload"] == {"key": "value"}
    finally:
        Path(tmp_path).unlink()
