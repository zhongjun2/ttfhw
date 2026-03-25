import time
from metrics.collector import MetricsCollector

def test_elapsed_records_wall_time():
    c = MetricsCollector()
    c.start("download")
    time.sleep(0.01)
    c.stop("download")
    assert c.elapsed("download") >= 0.01

def test_elapsed_returns_none_if_not_started():
    c = MetricsCollector()
    assert c.elapsed("download") is None

def test_add_error_appends():
    c = MetricsCollector()
    c.add_error("docker_pull_timeout")
    c.add_error("container_start_failed")
    assert c.errors == ["docker_pull_timeout", "container_start_failed"]

def test_status_pass_when_no_warn_or_fail():
    c = MetricsCollector()
    assert c.status() == "pass"

def test_status_warn():
    c = MetricsCollector()
    c.set_warn()
    assert c.status() == "warn"

def test_status_fail_overrides_warn():
    c = MetricsCollector()
    c.set_warn()
    c.set_fail()
    assert c.status() == "fail"

def test_to_dict_includes_all_fields():
    c = MetricsCollector()
    c.start("search")
    c.stop("search")
    c.add_error("no_result")
    c.set_warn()
    d = c.to_dict()
    assert "search_s" in d
    assert d["errors"] == ["no_result"]
    assert d["status"] == "warn"
