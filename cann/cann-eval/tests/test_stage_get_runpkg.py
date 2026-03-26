# tests/test_stage_get_runpkg.py
import pytest
from unittest.mock import patch, MagicMock, mock_open
from stages.stage_get_runpkg import GetRunPkgStage

BASE_CONFIG = {
    "run_pkg_url": "https://example.com/Ascend-cann-toolkit_9.0.run",
    "timeout": {"get_runpkg_s": 30},
}

def _make_stage(config=None):
    return GetRunPkgStage(config or BASE_CONFIG)

def test_runpkg_no_url_sets_fail():
    stage = GetRunPkgStage({"run_pkg_url": "", "timeout": {"get_runpkg_s": 10}})
    stage.setup()
    stage.run()
    assert stage.verify() is False

def test_runpkg_download_success():
    stage = _make_stage()
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"data" * 1024]
    mock_resp.raise_for_status = MagicMock()
    with patch("stages.stage_get_runpkg.requests.get", return_value=mock_resp), \
         patch("builtins.open", mock_open()), \
         patch("stages.stage_get_runpkg.tempfile.mkstemp", return_value=(0, "/tmp/test.run")), \
         patch("stages.stage_get_runpkg.subprocess.run") as mock_run, \
         patch("stages.stage_get_runpkg.os.chmod"), \
         patch("stages.stage_get_runpkg.os.path.getsize", return_value=4096):
        mock_run.return_value = MagicMock(returncode=1, stderr="permission denied")
        stage.setup()
        stage.run()
    m = stage.metrics()
    assert m["download_s"] is not None
    assert m["install_exit_code"] == 1

def test_runpkg_download_failure_sets_fail():
    stage = _make_stage()
    with patch("stages.stage_get_runpkg.requests.get", side_effect=Exception("timeout")):
        stage.setup()
        stage.run()
    assert stage.verify() is False
    m = stage.metrics()
    assert len(m["breakpoints"]) > 0
