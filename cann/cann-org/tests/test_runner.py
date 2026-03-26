import pytest
from unittest.mock import MagicMock, patch
from runner import Runner

def make_mock_stage(name, status="pass", verify_result=True):
    stage = MagicMock()
    stage.verify.return_value = verify_result
    stage.metrics.return_value = {"status": status, "errors": []}
    return stage

def test_runner_calls_all_lifecycle_methods():
    stage = make_mock_stage("learn")
    r = Runner(stages={"learn": stage}, config={"on_stage_failure": "continue"})
    r.run(["learn"])
    stage.setup.assert_called_once()
    stage.run.assert_called_once()
    stage.verify.assert_called_once()
    stage.teardown.assert_called_once()

def test_runner_collects_metrics_from_all_stages():
    stages = {
        "learn": make_mock_stage("learn"),
        "get": make_mock_stage("get"),
    }
    r = Runner(stages=stages, config={"on_stage_failure": "continue"})
    report = r.run(["learn", "get"])
    assert "learn" in report["stages"]
    assert "get" in report["stages"]

def test_runner_aborts_on_failure_when_configured():
    learn = make_mock_stage("learn", verify_result=False)
    get = make_mock_stage("get")
    r = Runner(stages={"learn": learn, "get": get}, config={"on_stage_failure": "abort"})
    r.run(["learn", "get"])
    get.setup.assert_not_called()

def test_runner_continues_on_failure_when_configured():
    learn = make_mock_stage("learn", verify_result=False)
    get = make_mock_stage("get")
    r = Runner(stages={"learn": learn, "get": get}, config={"on_stage_failure": "continue"})
    r.run(["learn", "get"])
    get.setup.assert_called_once()

def test_runner_includes_metadata_in_report():
    r = Runner(stages={}, config={"on_stage_failure": "continue",
                                   "cann_image": "toolkit:8.0.RC1"})
    report = r.run([])
    assert report["community"] == "cann"
    assert report["scenario"] == "zero-to-custom-op"
    assert "timestamp" in report
