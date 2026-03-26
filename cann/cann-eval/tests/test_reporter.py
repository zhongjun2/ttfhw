# tests/test_reporter.py
import json
from reports.reporter import Reporter

SAMPLE_REPORT = {
    "test_date": "2026-03-26T07:00:00Z",
    "mode": "auto",
    "environment": {"os": "Ubuntu 24.04", "arch": "x86_64"},
    "stages": {
        "learn": {
            "status": "warn", "search_s": 2.1,
            "official_link_rank": 1, "official_url": "https://hiascend.com",
            "quickstart_found": True, "qwen2_guide_found": False,
            "accessible_links": 2, "broken_links": 1,
            "breakpoints": [{"severity": "P2", "phenomenon": "断链", "cause": "URL 变更", "solution": "手动访问"}],
        },
        "get_docker": {
            "status": "pass", "net_download_s": 360.0, "image_size_mb": 4080.0,
            "atc_available": True, "cann_version": "version=9.0.0-beta.1",
            "wall_clock_s": 380.0,
            "breakpoints": [],
        },
        "get_runpkg": {
            "status": "warn", "download_s": 60.0, "file_size_mb": 500.0,
            "install_exit_code": 1, "atc_available": None,
            "breakpoints": [{"severity": "P1", "phenomenon": ".run 安装失败", "cause": "无 root", "solution": "用 sudo"}],
        },
        "use_quickstart": {
            "status": "pass", "atc_exit_code": 0, "atc_help_output": "ATC start working",
            "toolchain_s": 1.5,
            "breakpoints": [],
        },
        "use_qwen2": {
            "status": "pass", "inference_ok": True,
            "inference_output": "你好，我是 Qwen2",
            "model_size_mb": 950.0, "download_s": 120.0, "install_s": 30.0,
            "breakpoints": [],
        },
    },
    "breakpoints": [],
}

def test_to_json_returns_dict():
    r = Reporter(SAMPLE_REPORT)
    j = r.to_json()
    assert j["test_date"] == "2026-03-26T07:00:00Z"
    assert "stages" in j

def test_to_markdown_contains_key_sections():
    r = Reporter(SAMPLE_REPORT)
    md = r.to_markdown()
    assert "# CANN 易用性评估报告" in md
    assert "了解阶段" in md
    assert "获取阶段" in md
    assert "使用阶段" in md
    assert "断点汇总" in md
    assert "4080.0" in md   # image_size_mb from get_docker
    assert "总览" in md

def test_to_markdown_contains_breakpoint():
    r = Reporter(SAMPLE_REPORT)
    md = r.to_markdown()
    assert ".run 安装失败" in md
    assert "P1" in md

def test_to_markdown_shows_comparison():
    r = Reporter(SAMPLE_REPORT)
    md = r.to_markdown()
    assert "Docker" in md
    assert ".run" in md
