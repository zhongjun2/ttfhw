import pytest
from unittest.mock import MagicMock, patch
from stages.stage_get import GetStage

CONFIG = {
    "cann_image": "toolkit:8.0.RC1",
    "timeout": {"get_s": 600},
}

def test_verify_pass_when_cann_info_succeeds():
    stage = GetStage(CONFIG)
    with patch("stages.stage_get.docker") as mock_docker:
        client = MagicMock()
        mock_docker.from_env.return_value = client
        client.images.pull.return_value = MagicMock(id="sha256:abc")
        container = MagicMock()
        container.exec_run.return_value = MagicMock(exit_code=0, output=b"8.0.RC1\n")
        client.containers.run.return_value = container
        stage.setup()
        stage.run()
        assert stage.verify() is True

def test_verify_fail_when_pull_fails():
    stage = GetStage(CONFIG)
    with patch("stages.stage_get.docker") as mock_docker:
        client = MagicMock()
        mock_docker.from_env.return_value = client
        client.images.pull.side_effect = Exception("image not found")
        stage.setup()
        stage.run()
        assert stage.verify() is False
        assert any("docker_pull" in e for e in stage.metrics()["errors"])

def test_metrics_includes_required_fields():
    stage = GetStage(CONFIG)
    with patch("stages.stage_get.docker") as mock_docker:
        client = MagicMock()
        mock_docker.from_env.return_value = client
        img = MagicMock()
        img.attrs = {"Size": 8_600_000_000}
        client.images.pull.return_value = img
        container = MagicMock()
        container.exec_run.return_value = MagicMock(exit_code=0, output=b"8.0.RC1\n")
        client.containers.run.return_value = container
        stage.setup()
        stage.run()
        m = stage.metrics()
        for field in ["status", "wall_clock_s", "net_download_s",
                      "image_size_mb", "setup_steps", "errors"]:
            assert field in m
