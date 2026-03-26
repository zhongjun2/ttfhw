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

EMPTY_TOKEN_CONFIG = {
    "gitcode_token": "",
    "fork_repo": "ttfhw-bot/cann",
    "upstream_repo": "ascend/cann",
    "timeout": {"issue_response_s": 10, "ci_total_s": 30},
}

def test_issue_fails_immediately_when_token_empty():
    stage = ContributeStage(EMPTY_TOKEN_CONFIG)
    with patch("stages.stage_contribute.requests") as mock_req:
        stage.setup()
        stage.run_issue()
        assert mock_req.post.call_count == 0, "should not hit API when token is empty"
        m = stage.metrics()
        assert m["issue"]["status"] == "fail"
        assert any("gitcode_token_not_configured" in e for e in m["issue"]["errors"])

def test_pr_fails_immediately_when_token_empty():
    stage = ContributeStage(EMPTY_TOKEN_CONFIG)
    with patch("stages.stage_contribute.requests") as mock_req:
        stage.setup()
        stage.run_pr()
        assert mock_req.post.call_count == 0
        m = stage.metrics()
        assert m["pr_ci"]["status"] == "fail"
        assert any("gitcode_token_not_configured" in e for e in m["pr_ci"]["errors"])

def test_pr_uses_numeric_fork_project_id():
    stage = ContributeStage(CONFIG)
    with patch("stages.stage_contribute.requests") as mock_req, \
         patch("stages.stage_contribute.git") as mock_git, \
         patch("stages.stage_contribute.time.sleep"), \
         patch("builtins.open", MagicMock()):
        # GET /projects/ttfhw-bot%2Fcann → returns numeric ID 99
        project_lookup = MagicMock(status_code=200, json=MagicMock(return_value={"id": 99}))
        # POST /merge_requests → success
        mr_create = MagicMock(status_code=201, json=MagicMock(return_value={"iid": 5}))
        # GET /pipelines → success immediately
        pipeline_poll = MagicMock(
            json=MagicMock(return_value=[{"id": 1, "status": "success"}])
        )
        mock_req.get.side_effect = [project_lookup, pipeline_poll]
        mock_req.post.return_value = mr_create
        mock_git.Repo.clone_from.return_value = MagicMock()

        stage.setup()
        stage.run_pr()

        # Verify the MR payload used the resolved numeric ID, not the string path
        post_call_kwargs = mock_req.post.call_args[1]
        assert post_call_kwargs["json"]["source_project_id"] == 99

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
            MagicMock(status_code=200, json=MagicMock(return_value={"id": 42})),  # project_id lookup
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
