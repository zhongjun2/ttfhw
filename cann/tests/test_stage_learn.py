import pytest
from unittest.mock import patch, MagicMock
from stages.stage_learn import LearnStage

CONFIG = {
    "timeout": {"learn_s": 60},
    "search": {
        "engine": "bing",
        "bing_api_key": "test-key",
        "keywords": "Ascend CANN 快速入门",
        "official_domains": ["gitcode.com/ascend", "hiascend.com"]
    }
}

def make_search_response(urls):
    resp = MagicMock()
    resp.json.return_value = {"webPages": {"value": [{"url": u} for u in urls]}}
    resp.raise_for_status = MagicMock()
    return resp

def make_page_response(html, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.text = html
    resp.raise_for_status = MagicMock()
    return resp

def test_verify_pass_when_quickstart_found():
    stage = LearnStage(CONFIG)
    with patch("stages.stage_learn.requests.get") as mock_get, \
         patch("stages.stage_learn.requests.Session") as mock_session:
        mock_get.return_value = make_search_response(
            ["https://gitcode.com/ascend/cann"]
        )
        session = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)
        session.get.return_value = make_page_response(
            '<a href="/ascend/cann/quickstart">快速入门</a>'
        )
        stage.setup()
        stage.run()
        assert stage.verify() is True

def test_verify_fail_when_no_search_results():
    stage = LearnStage(CONFIG)
    with patch("stages.stage_learn.requests.get") as mock_get:
        mock_get.return_value = make_search_response([])
        stage.setup()
        stage.run()
        assert stage.verify() is False
        assert "search_no_results" in stage.metrics()["errors"]

def test_metrics_includes_required_fields():
    stage = LearnStage(CONFIG)
    with patch("stages.stage_learn.requests.get") as mock_get, \
         patch("stages.stage_learn.requests.Session") as mock_session:
        mock_get.return_value = make_search_response(
            ["https://gitcode.com/ascend/cann"]
        )
        session = MagicMock()
        mock_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_session.return_value.__exit__ = MagicMock(return_value=False)
        session.get.return_value = make_page_response("<html></html>")
        stage.setup()
        stage.run()
        m = stage.metrics()
        for field in ["status", "search_s", "official_link_rank", "nav_hops",
                      "accessible_links", "broken_links", "errors"]:
            assert field in m, f"Missing field: {field}"
