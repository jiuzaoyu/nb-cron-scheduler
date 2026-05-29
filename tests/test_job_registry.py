from unittest.mock import MagicMock

import pytest

from src.job_registry import register_jobs


class TestRegisterJobs:
    @pytest.fixture
    def mock_cron(self):
        cron = MagicMock()
        return cron

    @pytest.fixture
    def mock_publisher(self):
        publisher = MagicMock()
        return publisher

    @pytest.fixture
    def sample_jobs(self):
        return [
            {
                "name": "test_job_1",
                "cron": "*/5 * * * *",
                "stream": "cron:jobs:test_1",
                "payload": {"job_type": "test_1"},
                "timeout": 60,
                "max_retries": 1,
            },
            {
                "name": "test_job_2",
                "cron": "0 9 * * 1-5",
                "stream": "cron:jobs:test_2",
                "payload": {"job_type": "test_2"},
                "timeout": 300,
                "max_retries": 0,
            },
        ]

    def test_register_jobs_calls_add_job_for_each(self, mock_cron, mock_publisher, sample_jobs):
        register_jobs(mock_cron, mock_publisher, sample_jobs)

        assert mock_cron.add_job.call_count == 2

        # Verify first job registration
        first_call_args = mock_cron.add_job.call_args_list[0]
        assert first_call_args[1]["job_id"] == "test_job_1"
        assert first_call_args[1]["expression"] == "*/5 * * * *"
        assert first_call_args[1]["name"] == "test_job_1"

        # Verify second job registration
        second_call_args = mock_cron.add_job.call_args_list[1]
        assert second_call_args[1]["job_id"] == "test_job_2"
        assert second_call_args[1]["expression"] == "0 9 * * 1-5"

    def test_register_jobs_trigger_calls_publish(self, mock_cron, mock_publisher, sample_jobs):
        register_jobs(mock_cron, mock_publisher, sample_jobs)

        # Extract the function that was registered for the first job and call it
        func = mock_cron.add_job.call_args_list[0][0][0]
        func()

        mock_publisher.publish.assert_called_once_with(sample_jobs[0])

    def test_register_jobs_empty_list(self, mock_cron, mock_publisher):
        register_jobs(mock_cron, mock_publisher, [])
        mock_cron.add_job.assert_not_called()
