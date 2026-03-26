import pytest
from unittest.mock import MagicMock, patch
from stages.stage_use import UseStage

CONFIG = {"timeout": {"use_s": 300}}

def make_container(compile_output=b"BUILD_SUCCESS", compile_exit=0,
                   run_output=b"11.0,12.0,13.0,14.0,15.0,16.0,17.0,18.0",
                   run_exit=0):
    c = MagicMock()
    c.exec_run.side_effect = [
        MagicMock(exit_code=compile_exit, output=compile_output),
        MagicMock(exit_code=run_exit, output=run_output),
    ]
    return c

def test_verify_pass_when_output_matches():
    stage = UseStage(CONFIG)
    stage._container = make_container()
    stage.setup()
    stage.run()
    assert stage.verify() is True

def test_verify_fail_when_compile_fails():
    stage = UseStage(CONFIG)
    stage._container = make_container(compile_output=b"error: unknown", compile_exit=1)
    stage.setup()
    stage.run()
    assert stage.verify() is False
    m = stage.metrics()
    assert m["compile_errors"] > 0

def test_verify_fail_when_output_wrong():
    stage = UseStage(CONFIG)
    stage._container = make_container(run_output=b"0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0")
    stage.setup()
    stage.run()
    assert stage.verify() is False

def test_metrics_has_required_fields():
    stage = UseStage(CONFIG)
    stage._container = make_container()
    stage.setup()
    stage.run()
    m = stage.metrics()
    for f in ["status", "compile_s", "run_s", "compile_errors",
              "compile_warnings", "run_errors", "errors"]:
        assert f in m
