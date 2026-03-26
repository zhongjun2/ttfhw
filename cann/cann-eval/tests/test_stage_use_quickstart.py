# tests/test_stage_use_quickstart.py
from unittest.mock import MagicMock
from stages.stage_use_quickstart import UseQuickStartStage

BASE_CONFIG = {"timeout": {"use_quickstart_s": 30}}

def _make_stage_with_container(exit_code=0, output=b"ATC start working"):
    stage = UseQuickStartStage(BASE_CONFIG)
    mock_container = MagicMock()
    mock_container.exec_run.return_value = MagicMock(exit_code=exit_code, output=output)
    stage._container = mock_container
    return stage

def test_quickstart_atc_ok():
    stage = _make_stage_with_container(exit_code=0, output=b"ATC start working now")
    stage.setup()
    stage.run()
    assert stage.verify() is True
    m = stage.metrics()
    assert m["atc_exit_code"] == 0
    assert "ATC" in m["atc_help_output"]

def test_quickstart_atc_fail_sets_warn():
    stage = _make_stage_with_container(exit_code=1, output=b"error")
    stage.setup()
    stage.run()
    m = stage.metrics()
    assert m["atc_exit_code"] == 1

def test_quickstart_no_container_sets_fail():
    stage = UseQuickStartStage(BASE_CONFIG)
    stage.setup()
    stage.run()
    assert stage.verify() is False
