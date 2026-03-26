# tests/test_collector.py
import pytest
from metrics.collector import MetricsCollector

def test_elapsed_after_start_stop():
    mc = MetricsCollector()
    mc.start("download")
    mc.stop("download")
    assert mc.elapsed("download") >= 0

def test_elapsed_returns_none_if_not_stopped():
    mc = MetricsCollector()
    mc.start("download")
    assert mc.elapsed("download") is None

def test_status_default_pass():
    mc = MetricsCollector()
    assert mc.status() == "pass"

def test_status_warn():
    mc = MetricsCollector()
    mc.set_warn()
    assert mc.status() == "warn"

def test_status_fail_overrides_warn():
    mc = MetricsCollector()
    mc.set_warn()
    mc.set_fail()
    assert mc.status() == "fail"

def test_add_error_stores_breakpoint():
    mc = MetricsCollector()
    mc.add_error("DNS 解析失败", severity="P1", cause="内网域名", solution="使用 Docker Hub 替代")
    d = mc.to_dict()
    assert len(d["breakpoints"]) == 1
    bp = d["breakpoints"][0]
    assert bp["severity"] == "P1"
    assert bp["phenomenon"] == "DNS 解析失败"
    assert bp["cause"] == "内网域名"
    assert bp["solution"] == "使用 Docker Hub 替代"

def test_to_dict_includes_elapsed():
    mc = MetricsCollector()
    mc.start("net")
    mc.stop("net")
    d = mc.to_dict()
    assert "net_s" in d
    assert d["net_s"] >= 0

def test_to_dict_status_field():
    mc = MetricsCollector()
    d = mc.to_dict()
    assert d["status"] == "pass"
