import pytest
from unittest.mock import MagicMock, patch
from stages.stage_contribute import ContributeStage

CONFIG = {
    "gitcode_token": "test-token",
    "fork_repo": "ttfhw-bot/cann",
    "upstream_repo": "ascend/cann",
    "timeout": {"issue_response_s": 10, "ci_total_s": 30},
}

def test_issue_submit_records_metrics():
    stage = ContributeStage(CONFIG)
    with patch("stages.stage_contribute.requests") as mock_req, \
         patch("stages.stage_contribute.time.sleep"):
        mock_req.post.return_value = MagicMock(
            status_code=201,
            json=MagicMock(return_value={"iid": 42})
        )
        mock_req.get.return_value = MagicMock(
            json=MagicMock(return_value=[{"id": 1}])
        )
        stage.setup()
        stage.run_issue()
        m = stage.metrics()
        assert m["issue"]["status"] in ("pass", "warn", "fail")
        assert "submit_s" in m["issue"]

def test_issue_fail_on_api_error():
    stage = ContributeStage(CONFIG)
    with patch("stages.stage_contribute.requests") as mock_req, \
         patch("stages.stage_contribute.time.sleep"):
        mock_req.post.return_value = MagicMock(status_code=401, json=MagicMock(return_value={}))
        stage.setup()
        stage.run_issue()
        m = stage.metrics()
        assert m["issue"]["status"] == "fail"

def test_pr_ci_metrics_recorded():
    stage = ContributeStage(CONFIG)
    with patch("stages.stage_contribute.requests") as mock_req, \
         patch("stages.stage_contribute.git") as mock_git, \
         patch("stages.stage_contribute.time.sleep"), \
         patch("builtins.open", MagicMock()):
        mock_req.post.return_value = MagicMock(
            status_code=201, json=MagicMock(return_value={"iid": 7})
        )
        mock_req.get.side_effect = [
            MagicMock(json=MagicMock(return_value=[{"id": 1, "status": "running"}])),
            MagicMock(json=MagicMock(return_value=[{"id": 1, "status": "success",
                                                     "jobs": [{"name": "test", "status": "success"}]}])),
        ]
        mock_git.Repo.clone_from.return_value = MagicMock()
        stage.setup()
        stage.run_pr()
        m = stage.metrics()
        assert "pr_ci" in m
        for field in ["submit_s", "ci_queue_s", "ci_prepare_s", "ci_run_s",
                      "ci_total_s", "ci_result", "errors"]:
            assert field in m["pr_ci"]
