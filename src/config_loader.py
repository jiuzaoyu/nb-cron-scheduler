from typing import Any

import yaml


def load_scheduler_config(config_path: str) -> dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_job_definitions(definitions_path: str) -> list[dict[str, Any]]:
    with open(definitions_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("jobs", [])
