# tests/test_stage_learn.py
import pytest
from unittest.mock import patch, MagicMock
from stages.stage_learn import LearnStage

BASE_CONFIG = {
    "quickstart_url": "https://www.hiascend.com/quickstart",
    "timeout": {"learn_s": 10},
}

def _make_stage(config=None):
    return LearnStage(config or BASE_CONFIG)

def test_learn_finds_official_link():
    stage = _make_stage()
    search_results = [
        "https://www.hiascend.com/document/detail/zh/CANNCommunityEdition",
        "https://other.com/cann",
    ]
    with patch("stages.stage_learn.search", return_value=search_results), \
         patch("stages.stage_learn.requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=200)
        stage.setup()
        stage.run()
    m = stage.metrics()
    assert m["official_link_rank"] == 1
    assert m["official_accessible"] is True

def test_learn_no_official_link_sets_fail():
    stage = _make_stage()
    with patch("stages.stage_learn.search", return_value=["https://other.com"]), \
         patch("stages.stage_learn.requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=200)
        stage.setup()
        stage.run()
    assert stage.verify() is False
    m = stage.metrics()
    assert m["official_link_rank"] is None

def test_learn_search_exception_sets_fail():
    stage = _make_stage()
    with patch("stages.stage_learn.search", side_effect=Exception("timeout")):
        stage.setup()
        stage.run()
    assert stage.verify() is False
    m = stage.metrics()
    assert len(m["breakpoints"]) > 0

def test_learn_broken_link_sets_warn():
    stage = _make_stage()
    search_results = ["https://www.hiascend.com/doc"]
    with patch("stages.stage_learn.search", return_value=search_results), \
         patch("stages.stage_learn.requests.head") as mock_head:
        mock_head.return_value = MagicMock(status_code=404)
        stage.setup()
        stage.run()
    assert stage.metrics()["broken_links"] >= 1
