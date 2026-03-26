# tests/test_stage_get_docker.py
import pytest
from unittest.mock import patch, MagicMock
from stages.stage_get_docker import GetDockerStage

BASE_CONFIG = {
    "cann_image": "ascendai/cann:latest",
    "timeout": {"get_docker_s": 30},
}

def _make_stage(config=None):
    return GetDockerStage(config or BASE_CONFIG)

def test_get_docker_pull_success():
    stage = _make_stage()
    mock_client = MagicMock()
    mock_img = MagicMock()
    mock_img.attrs = {"Size": 4 * 1024 * 1024 * 1024}
    mock_client.images.pull.return_value = mock_img
    mock_container = MagicMock()
    mock_container.exec_run.return_value = MagicMock(exit_code=0, output=b"ATC start working")
    mock_client.containers.run.return_value = mock_container
    with patch("stages.stage_get_docker.docker.from_env", return_value=mock_client):
        stage.setup()
        stage.run()
    assert stage.verify() is True
    m = stage.metrics()
    assert m["image_size_mb"] == pytest.approx(4096.0, abs=1)
    assert m["atc_available"] is True

def test_get_docker_pull_failure_sets_fail():
    stage = _make_stage()
    mock_client = MagicMock()
    mock_client.images.pull.side_effect = Exception("pull failed")
    with patch("stages.stage_get_docker.docker.from_env", return_value=mock_client):
        stage.setup()
        stage.run()
    assert stage.verify() is False
    m = stage.metrics()
    assert len(m["breakpoints"]) > 0

def test_get_docker_atc_not_available_sets_warn():
    stage = _make_stage()
    mock_client = MagicMock()
    mock_img = MagicMock()
    mock_img.attrs = {"Size": 1024}
    mock_client.images.pull.return_value = mock_img
    mock_container = MagicMock()
    mock_container.exec_run.return_value = MagicMock(exit_code=1, output=b"not found")
    mock_client.containers.run.return_value = mock_container
    with patch("stages.stage_get_docker.docker.from_env", return_value=mock_client):
        stage.setup()
        stage.run()
    assert stage.metrics()["atc_available"] is False

def test_get_docker_teardown_does_not_stop_if_container_none():
    stage = _make_stage()
    stage.teardown()  # should not raise
