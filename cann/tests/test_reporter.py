import json
from reports.reporter import Reporter

SAMPLE_DATA = {
    "community": "cann",
    "scenario": "zero-to-custom-op",
    "timestamp": "2026-03-25T10:00:00Z",
    "cann_version": "8.0.RC1",
    "stages": {
        "learn": {"status": "pass", "search_s": 2.1, "official_link_rank": 1,
                  "nav_hops": 2, "accessible_links": 45, "broken_links": 0, "errors": []},
        "get": {"status": "pass", "wall_clock_s": 180.5, "net_download_s": 165.2,
                "image_size_mb": 8200, "setup_steps": 5, "errors": []},
        "use": {"status": "pass", "compile_s": 45.1, "run_s": 2.3,
                "compile_errors": 0, "compile_warnings": 0, "run_errors": 0, "errors": []},
        "contribute": {
            "issue": {"status": "pass", "submit_s": 1.2, "first_response_s": 300, "errors": []},
            "pr_ci": {"status": "pass", "submit_s": 2.1, "ci_queue_s": 120,
                      "ci_prepare_s": 45, "ci_run_s": 600, "ci_total_s": 768,
                      "ci_result": "success", "errors": []}
        }
    }
}

def test_to_json_is_valid():
    r = Reporter(SAMPLE_DATA)
    output = r.to_json()
    parsed = json.loads(json.dumps(output))
    assert parsed["community"] == "cann"
    assert parsed["stages"]["learn"]["status"] == "pass"

def test_to_markdown_contains_stage_names():
    r = Reporter(SAMPLE_DATA)
    md = r.to_markdown()
    for stage in ["了解", "获取", "使用", "贡献-Issue", "贡献-PR CI"]:
        assert stage in md

def test_to_markdown_contains_anomaly_section():
    r = Reporter(SAMPLE_DATA)
    md = r.to_markdown()
    assert "异常记录" in md

def test_to_markdown_lists_errors_when_present():
    data = dict(SAMPLE_DATA)
    data["stages"] = dict(SAMPLE_DATA["stages"])
    data["stages"]["learn"] = {**SAMPLE_DATA["stages"]["learn"],
                                "status": "fail",
                                "errors": ["search_no_results"]}
    r = Reporter(data)
    md = r.to_markdown()
    assert "search_no_results" in md
