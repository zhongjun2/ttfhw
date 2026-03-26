# CANN TTFHW Automated Testing Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully automated, modular framework that measures developer time and quality metrics across four stages (Learn, Get, Use, Contribute) of the Ascend CANN community, exposing results via MCP tools and Claude Skills.

**Architecture:** A Python package with a `BaseStage` interface implemented by four stage modules, orchestrated by a `Runner` that collects metrics into a unified `MetricsCollector` and outputs JSON + Markdown reports. An `mcp_server.py` wraps the runner as MCP tools, and Skill definition files provide Claude Code slash commands.

**Tech Stack:** Python 3.10+, `requests` (HTTP/search), `docker` SDK (container management), `gitpython` + Gitcode REST API (contribute stage), `mcp` Python SDK (MCP server), `pytest` (tests), `pyyaml` (config).

---

## File Map

```
ttfhw-cann/
├── config.yaml                        # Runtime configuration (image, token, timeouts)
├── runner.py                          # Orchestrates all stages, returns aggregated report
├── stages/
│   ├── __init__.py
│   ├── base.py                        # BaseStage ABC with setup/run/verify/teardown/metrics
│   ├── stage_learn.py                 # Stage 1: search → navigate → verify links
│   ├── stage_get.py                   # Stage 2: docker pull → start → verify cann-info
│   ├── stage_use.py                   # Stage 3: copy fixtures → compile → run → verify output
│   └── stage_contribute.py            # Stage 4: submit Issue + PR, poll CI timings
├── metrics/
│   ├── __init__.py
│   └── collector.py                   # Timestamping, error capture, status determination
├── reports/
│   ├── __init__.py
│   └── reporter.py                    # Renders collected metrics → JSON dict + Markdown string
├── fixtures/
│   └── custom_op/
│       ├── add_custom.cpp             # AiCPU AddCustom operator source
│       ├── build.sh                   # Compile script (runs inside container)
│       ├── run.py                     # Inference script (runs inside container)
│       └── expected_output.txt        # Reference values for verification
├── mcp_server.py                      # MCP server: exposes run_all, run_stage, report tools
├── skills/
│   ├── cann-ttfhw.md                  # /cann-ttfhw skill definition
│   ├── cann-learn.md                  # /cann-learn skill definition
│   ├── cann-get.md                    # /cann-get skill definition
│   ├── cann-use.md                    # /cann-use skill definition
│   ├── cann-contribute.md             # /cann-contribute skill definition
│   ├── cann-contribute-issue.md       # /cann-contribute-issue skill definition
│   └── cann-contribute-pr.md         # /cann-contribute-pr skill definition
└── tests/
    ├── test_base.py                   # BaseStage interface contract tests
    ├── test_metrics.py                # MetricsCollector unit tests
    ├── test_reporter.py               # Reporter output format tests
    ├── test_runner.py                 # Runner orchestration tests (mocked stages)
    ├── test_stage_learn.py            # Learn stage tests (mocked HTTP/search)
    ├── test_stage_get.py              # Get stage tests (mocked docker SDK)
    ├── test_stage_use.py              # Use stage tests (mocked container exec)
    └── test_stage_contribute.py       # Contribute stage tests (mocked Gitcode API)
```

---

## Task 1: Project Scaffold and Config

**Files:**
- Create: `config.yaml`
- Create: `stages/__init__.py`
- Create: `metrics/__init__.py`
- Create: `reports/__init__.py`
- Create: `requirements.txt`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create project root files**

```bash
mkdir -p stages metrics reports fixtures/custom_op tests skills
touch stages/__init__.py metrics/__init__.py reports/__init__.py tests/__init__.py
```

- [ ] **Step 2: Create `requirements.txt`**

```
requests>=2.31.0
docker>=7.0.0
gitpython>=3.1.40
pyyaml>=6.0
mcp>=1.0.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without error.

- [ ] **Step 4: Create `config.yaml`**

```yaml
cann_image: "ascendhub.huawei.com/public-ascendhub/ascend-toolkit:8.0.RC1"
gitcode_token: "${GITCODE_TOKEN}"
fork_repo: "ttfhw-bot/cann"
upstream_repo: "ascend/cann"

timeout:
  learn_s: 60
  get_s: 600
  use_s: 300
  issue_response_s: 3600
  ci_total_s: 7200

on_stage_failure: continue   # continue | abort

search:
  engine: "bing"
  bing_api_key: "${BING_API_KEY}"   # Set env var BING_API_KEY before running
  keywords: "Ascend CANN 快速入门"
  official_domains:
    - "gitcode.com/ascend"
    - "hiascend.com"
```

- [ ] **Step 5: Commit scaffold**

```bash
git init
git add .
git commit -m "chore: initial project scaffold and config"
```

---

## Task 2: MetricsCollector

**Files:**
- Create: `metrics/collector.py`
- Test: `tests/test_metrics.py`

The collector is a lightweight object each Stage holds. It records start/end times per named checkpoint, accumulates error messages, and computes a `status` string (`pass`/`warn`/`fail`) given explicit boolean flags set by the stage.

- [ ] **Step 1: Write failing tests for MetricsCollector**

Create `tests/test_metrics.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_metrics.py -v
```

Expected: `ModuleNotFoundError` or similar — `collector.py` does not exist yet.

- [ ] **Step 3: Implement `metrics/collector.py`**

```python
import time


class MetricsCollector:
    def __init__(self):
        self._starts: dict[str, float] = {}
        self._stops: dict[str, float] = {}
        self.errors: list[str] = []
        self._warn = False
        self._fail = False

    def start(self, name: str) -> None:
        self._starts[name] = time.monotonic()

    def stop(self, name: str) -> None:
        self._stops[name] = time.monotonic()

    def elapsed(self, name: str) -> float | None:
        if name not in self._starts or name not in self._stops:
            return None
        return round(self._stops[name] - self._starts[name], 3)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def set_warn(self) -> None:
        self._warn = True

    def set_fail(self) -> None:
        self._fail = True

    def status(self) -> str:
        if self._fail:
            return "fail"
        if self._warn:
            return "warn"
        return "pass"

    def to_dict(self) -> dict:
        result = {"status": self.status(), "errors": self.errors}
        for name in self._stops:
            result[f"{name}_s"] = self.elapsed(name)
        return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_metrics.py -v
```

Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add metrics/collector.py tests/test_metrics.py
git commit -m "feat: add MetricsCollector with timing, error tracking, and status"
```

---

## Task 3: BaseStage ABC

**Files:**
- Create: `stages/base.py`
- Test: `tests/test_base.py`

`BaseStage` is an abstract class. Concrete stages must implement `setup`, `run`, `verify`, `teardown`, and `metrics`. Runner calls them in order.

- [ ] **Step 1: Write failing test**

Create `tests/test_base.py`:

```python
import pytest
from stages.base import BaseStage

def test_base_stage_is_abstract():
    with pytest.raises(TypeError):
        BaseStage()

def test_concrete_stage_must_implement_all_methods():
    class Incomplete(BaseStage):
        pass
    with pytest.raises(TypeError):
        Incomplete()

def test_concrete_stage_can_be_instantiated():
    class Complete(BaseStage):
        def setup(self): pass
        def run(self): pass
        def verify(self) -> bool: return True
        def teardown(self): pass
        def metrics(self) -> dict: return {}
    stage = Complete()
    assert stage.verify() is True
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_base.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `stages/base.py`**

```python
from abc import ABC, abstractmethod


class BaseStage(ABC):
    @abstractmethod
    def setup(self) -> None: ...

    @abstractmethod
    def run(self) -> None: ...

    @abstractmethod
    def verify(self) -> bool: ...

    @abstractmethod
    def teardown(self) -> None: ...

    @abstractmethod
    def metrics(self) -> dict: ...
```

- [ ] **Step 4: Run to verify pass**

```bash
pytest tests/test_base.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add stages/base.py tests/test_base.py
git commit -m "feat: add BaseStage abstract class"
```

---

## Task 4: Reporter

**Files:**
- Create: `reports/reporter.py`
- Test: `tests/test_reporter.py`

Reporter takes the full collected data dict and renders it as JSON-serializable dict and Markdown string. It does not perform I/O — callers write to disk or print.

- [ ] **Step 1: Write failing tests**

Create `tests/test_reporter.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_reporter.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `reports/reporter.py`**

```python
import json


class Reporter:
    def __init__(self, data: dict):
        self._data = data

    def to_json(self) -> dict:
        return self._data

    def to_markdown(self) -> str:
        d = self._data
        stages = d.get("stages", {})
        learn = stages.get("learn", {})
        get = stages.get("get", {})
        use = stages.get("use", {})
        issue = stages.get("contribute", {}).get("issue", {})
        pr_ci = stages.get("contribute", {}).get("pr_ci", {})

        def icon(s): return "✅" if s == "pass" else ("⚠️" if s == "warn" else "❌")

        rows = [
            f"| 了解 | {icon(learn.get('status',''))} {learn.get('status','')} "
            f"| 搜索 {learn.get('search_s','?')}s，导航 {learn.get('nav_hops','?')} 跳 "
            f"| 官方链接排名第{learn.get('official_link_rank','?')} |",
            f"| 获取 | {icon(get.get('status',''))} {get.get('status','')} "
            f"| 总计 {get.get('wall_clock_s','?')}s，下载 {get.get('net_download_s','?')}s "
            f"| 镜像 {get.get('image_size_mb','?')}MB |",
            f"| 使用 | {icon(use.get('status',''))} {use.get('status','')} "
            f"| 编译 {use.get('compile_s','?')}s，运行 {use.get('run_s','?')}s | 无报错 |",
            f"| 贡献-Issue | {icon(issue.get('status',''))} {issue.get('status','')} "
            f"| 提交 {issue.get('submit_s','?')}s，首次响应 {issue.get('first_response_s','?')}s | — |",
            f"| 贡献-PR CI | {icon(pr_ci.get('status',''))} {pr_ci.get('status','')} "
            f"| 排队 {pr_ci.get('ci_queue_s','?')}s，准备 {pr_ci.get('ci_prepare_s','?')}s，"
            f"运行 {pr_ci.get('ci_run_s','?')}s | CI结果: {pr_ci.get('ci_result','?')} |",
        ]

        all_errors = []
        for stage_name, stage_data in stages.items():
            if isinstance(stage_data, dict):
                for err in stage_data.get("errors", []):
                    all_errors.append(f"- [{stage_name}] {err}")
                for sub in stage_data.values():
                    if isinstance(sub, dict):
                        for err in sub.get("errors", []):
                            all_errors.append(f"- [{stage_name}] {err}")

        anomalies = "\n".join(all_errors) if all_errors else "（无）"

        return f"""# CANN TTFHW 测试报告

**时间：** {d.get('timestamp', '')}
**CANN 版本：** {d.get('cann_version', '')}
**场景：** {d.get('scenario', '')}

## 各阶段耗时汇总

| 阶段 | 状态 | 关键时间 | 备注 |
|------|------|---------|------|
{chr(10).join(rows)}

## 异常记录

{anomalies}
"""

```

- [ ] **Step 4: Run to verify pass**

```bash
pytest tests/test_reporter.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add reports/reporter.py tests/test_reporter.py
git commit -m "feat: add Reporter with JSON and Markdown output"
```

---

## Task 5: Runner

**Files:**
- Create: `runner.py`
- Test: `tests/test_runner.py`

Runner loads config, instantiates each stage, calls `setup → run → verify → teardown`, and assembles the final report dict. Respects `on_stage_failure: continue | abort`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_runner.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_runner.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `runner.py`**

```python
import datetime
from stages.base import BaseStage


class Runner:
    COMMUNITY = "cann"
    SCENARIO = "zero-to-custom-op"

    def __init__(self, stages: dict[str, BaseStage], config: dict):
        self._stages = stages
        self._config = config

    def run(self, stage_names: list[str]) -> dict:
        report = {
            "community": self.COMMUNITY,
            "scenario": self.SCENARIO,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "cann_version": self._config.get("cann_image", "unknown").split(":")[-1],
            "stages": {},
        }
        abort_on_failure = self._config.get("on_stage_failure", "continue") == "abort"
        completed: dict[str, BaseStage] = {}

        for name in stage_names:
            stage = self._stages.get(name)
            if stage is None:
                continue
            # Wire container from GetStage into UseStage before running Use
            if name == "use" and "get" in completed:
                stage._container = completed["get"]._container
            try:
                stage.setup()
                stage.run()
                ok = stage.verify()
                stage.teardown()
            except Exception as e:
                ok = False
                stage.teardown()
            completed[name] = stage
            report["stages"][name] = stage.metrics()
            if not ok and abort_on_failure:
                break

        return report
```

- [ ] **Step 4: Run to verify pass**

```bash
pytest tests/test_runner.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add runner.py tests/test_runner.py
git commit -m "feat: add Runner with stage orchestration and abort/continue logic"
```

---

## Task 6: AiCPU AddCustom Fixture

**Files:**
- Create: `fixtures/custom_op/add_custom.cpp`
- Create: `fixtures/custom_op/build.sh`
- Create: `fixtures/custom_op/run.py`
- Create: `fixtures/custom_op/expected_output.txt`

This fixture is the standard operator used in the Use stage. It adds a scalar to each element of a 1D float32 tensor using the AiCPU kernel interface. It must compile and run under CANN AiCPU simulation (CPU mode, no physical NPU).

- [ ] **Step 1: Create `fixtures/custom_op/add_custom.cpp`**

```cpp
#include "cpu_kernel_utils.h"
#include <vector>
#include <stdint.h>

extern "C" __attribute__((visibility("default")))
uint32_t AddCustom(void* x, void* scalar, void* y, int64_t n) {
    float* in = static_cast<float*>(x);
    float s = *static_cast<float*>(scalar);
    float* out = static_cast<float*>(y);
    for (int64_t i = 0; i < n; ++i) {
        out[i] = in[i] + s;
    }
    return 0;
}
```

- [ ] **Step 2: Create `fixtures/custom_op/build.sh`**

```bash
#!/bin/bash
set -e
source /usr/local/Ascend/ascend-toolkit/set_env.sh
g++ -shared -fPIC -o add_custom.so add_custom.cpp \
    -I${ASCEND_TOOLKIT_HOME}/include \
    -L${ASCEND_TOOLKIT_HOME}/lib64 \
    -lascend_hal 2>&1
echo "BUILD_SUCCESS"
```

- [ ] **Step 3: Create `fixtures/custom_op/run.py`**

```python
import ctypes, os, numpy as np

lib = ctypes.CDLL(os.path.join(os.path.dirname(__file__), "add_custom.so"))
lib.AddCustom.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int64
]
lib.AddCustom.restype = ctypes.c_uint32

n = 8
x = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float32)
scalar = np.array([10.0], dtype=np.float32)
y = np.zeros(n, dtype=np.float32)

ret = lib.AddCustom(
    x.ctypes.data_as(ctypes.c_void_p),
    scalar.ctypes.data_as(ctypes.c_void_p),
    y.ctypes.data_as(ctypes.c_void_p),
    ctypes.c_int64(n)
)
assert ret == 0, f"Kernel returned error code {ret}"
print(",".join(f"{v:.1f}" for v in y))
```

- [ ] **Step 4: Create `fixtures/custom_op/expected_output.txt`**

```
11.0,12.0,13.0,14.0,15.0,16.0,17.0,18.0
```

- [ ] **Step 5: Commit**

```bash
git add fixtures/
git commit -m "feat: add AiCPU AddCustom operator fixture"
```

---

## Task 7: Stage 1 — Learn

**Files:**
- Create: `stages/stage_learn.py`
- Test: `tests/test_stage_learn.py`

Calls a search API, identifies official links by domain matching, navigates to the quickstart page (up to 5 hops), checks link reachability.

- [ ] **Step 1: Write failing tests**

Create `tests/test_stage_learn.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from stages.stage_learn import LearnStage

CONFIG = {
    "timeout": {"learn_s": 60},
    "search": {
        "engine": "bing",
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
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_stage_learn.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `stages/stage_learn.py`**

```python
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from stages.base import BaseStage
from metrics.collector import MetricsCollector


class LearnStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._official_url: str | None = None
        self._rank: int | None = None
        self._nav_hops: int = 0
        self._accessible: int = 0
        self._broken: int = 0

    def setup(self) -> None:
        pass

    def run(self) -> None:
        search_cfg = self._config.get("search", {})
        keywords = search_cfg.get("keywords", "Ascend CANN")
        domains = search_cfg.get("official_domains", [])
        timeout = self._config.get("timeout", {}).get("learn_s", 60)

        self._mc.start("search")
        results = self._search(keywords, timeout)
        self._mc.stop("search")        if not results:
            self._mc.add_error("search_no_results")
            self._mc.set_fail()
            return

        self._official_url, self._rank = self._find_official(results, domains)
        if not self._official_url:
            self._mc.add_error("no_official_link_found")
            self._mc.set_fail()
            return

        self._navigate_to_quickstart(timeout)
        self._check_links(timeout)

    def _search(self, keywords: str, timeout: int) -> list[str]:
        # NOTE: Bing Search API requires an API key in config.yaml:
        #   search.bing_api_key: "${BING_API_KEY}"
        # Without it, the call returns HTTP 401. Set env var BING_API_KEY before running.
        try:
            search_cfg = self._config.get("search", {})
            api_key = search_cfg.get("bing_api_key", "")
            r = requests.get(
                "https://api.bing.microsoft.com/v7.0/search",
                params={"q": keywords, "count": 10},
                headers={"Ocp-Apim-Subscription-Key": api_key},
                timeout=timeout,
            )
            r.raise_for_status()
            pages = r.json().get("webPages", {}).get("value", [])
            return [p["url"] for p in pages]
        except Exception as e:
            self._mc.add_error(f"search_error: {e}")
            return []

    def _find_official(self, urls: list[str], domains: list[str]):
        for i, url in enumerate(urls, start=1):
            if any(d in url for d in domains):
                return url, i
        return None, None

    def _navigate_to_quickstart(self, timeout: int) -> None:
        url = self._official_url
        hops = 0
        max_hops = 5
        with requests.Session() as session:
            while hops < max_hops:
                try:
                    resp = session.get(url, timeout=timeout)
                    hops += 1
                    if "快速入门" in resp.text or "quickstart" in resp.text.lower():
                        self._nav_hops = hops
                        return
                    soup = BeautifulSoup(resp.text, "html.parser")
                    link = soup.find("a", string=lambda t: t and "快速入门" in t)
                    if link:
                        url = urljoin(url, link["href"])
                    else:
                        break
                except Exception:
                    break
        self._nav_hops = hops
        if hops >= max_hops:
            self._mc.add_error("quickstart_not_reachable")
            self._mc.set_fail()

    def _check_links(self, timeout: int) -> None:
        try:
            with requests.Session() as session:
                resp = session.get(self._official_url, timeout=timeout)
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("http"):
                        try:
                            r = session.head(href, timeout=5, allow_redirects=True)
                            if r.status_code < 400:
                                self._accessible += 1
                            else:
                                self._broken += 1
                                self._mc.set_warn()
                        except Exception:
                            self._broken += 1
                            self._mc.set_warn()
        except Exception as e:
            self._mc.add_error(f"link_check_error: {e}")

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        pass

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "official_link_rank": self._rank,
            "nav_hops": self._nav_hops,
            "accessible_links": self._accessible,
            "broken_links": self._broken,
        })
        return d
```

- [ ] **Step 4: Add `beautifulsoup4` to requirements and install**

```bash
echo "beautifulsoup4>=4.12.0" >> requirements.txt
pip install beautifulsoup4
```

- [ ] **Step 5: Run to verify pass**

```bash
pytest tests/test_stage_learn.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add stages/stage_learn.py tests/test_stage_learn.py requirements.txt
git commit -m "feat: add LearnStage (search → navigate → link check)"
```

---

## Task 8: Stage 2 — Get

**Files:**
- Create: `stages/stage_get.py`
- Test: `tests/test_stage_get.py`

Pulls the official CANN Docker image, starts a container, and verifies the CANN toolchain is available inside.

- [ ] **Step 1: Write failing tests**

Create `tests/test_stage_get.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from stages.stage_get import GetStage

CONFIG = {
    "cann_image": "toolkit:8.0.RC1",
    "timeout": {"get_s": 600},
}

def test_verify_pass_when_cann_info_succeeds():
    stage = GetStage(CONFIG)
    with patch("stages.stage_get.docker") as mock_docker:
        client = MagicMock()
        mock_docker.from_env.return_value = client
        client.images.pull.return_value = MagicMock(id="sha256:abc")
        container = MagicMock()
        container.exec_run.return_value = MagicMock(exit_code=0, output=b"8.0.RC1\n")
        client.containers.run.return_value = container
        stage.setup()
        stage.run()
        assert stage.verify() is True

def test_verify_fail_when_pull_fails():
    stage = GetStage(CONFIG)
    with patch("stages.stage_get.docker") as mock_docker:
        client = MagicMock()
        mock_docker.from_env.return_value = client
        client.images.pull.side_effect = Exception("image not found")
        stage.setup()
        stage.run()
        assert stage.verify() is False
        assert any("docker_pull" in e for e in stage.metrics()["errors"])

def test_metrics_includes_required_fields():
    stage = GetStage(CONFIG)
    with patch("stages.stage_get.docker") as mock_docker:
        client = MagicMock()
        mock_docker.from_env.return_value = client
        img = MagicMock()
        img.attrs = {"Size": 8_600_000_000}
        client.images.pull.return_value = img
        container = MagicMock()
        container.exec_run.return_value = MagicMock(exit_code=0, output=b"8.0.RC1\n")
        client.containers.run.return_value = container
        stage.setup()
        stage.run()
        m = stage.metrics()
        for field in ["status", "wall_clock_s", "net_download_s",
                      "image_size_mb", "setup_steps", "errors"]:
            assert field in m
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_stage_get.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `stages/stage_get.py`**

```python
import docker
import time
from stages.base import BaseStage
from metrics.collector import MetricsCollector


class GetStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._client = None
        self._container = None
        self._image_size_mb: float | None = None
        self._setup_steps: int = 0

    def setup(self) -> None:
        self._client = docker.from_env()

    def run(self) -> None:
        image_name = self._config.get("cann_image", "")
        timeout = self._config.get("timeout", {}).get("get_s", 600)

        self._mc.start("wall_clock")
        self._mc.start("net_download")
        try:
            img = self._client.images.pull(image_name, timeout=timeout)
            self._mc.stop("net_download")
            self._image_size_mb = round(
                img.attrs.get("Size", 0) / (1024 * 1024), 1
            )
        except Exception as e:
            self._mc.stop("net_download")
            self._mc.add_error(f"docker_pull_error: {e}")
            self._mc.set_fail()
            self._mc.stop("wall_clock")
            return

        try:
            self._container = self._client.containers.run(
                image_name, detach=True, tty=True
            )
            self._setup_steps += 1
        except Exception as e:
            self._mc.add_error(f"container_start_failed: {e}")
            self._mc.set_fail()
            self._mc.stop("wall_clock")
            return

        result = self._container.exec_run("cann-info")
        self._setup_steps += 1
        if result.exit_code != 0:
            self._mc.add_error("cann_info_not_found")
            self._mc.set_fail()

        self._mc.stop("wall_clock")

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        if self._container:
            try:
                self._container.stop()
                self._container.remove()
            except Exception:
                pass

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        wall = self._mc.elapsed("wall_clock")
        net = self._mc.elapsed("net_download")
        d.update({
            "wall_clock_s": wall,
            "net_download_s": net,
            "image_size_mb": self._image_size_mb,
            "setup_steps": self._setup_steps,
        })
        d.pop("wall_clock_s", None)
        d.pop("net_download_s", None)
        d["wall_clock_s"] = wall
        d["net_download_s"] = net
        return d
```

- [ ] **Step 4: Run to verify pass**

```bash
pytest tests/test_stage_get.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add stages/stage_get.py tests/test_stage_get.py
git commit -m "feat: add GetStage (docker pull → start → cann-info verify)"
```

---

## Task 9: Stage 3 — Use

**Files:**
- Create: `stages/stage_use.py`
- Test: `tests/test_stage_use.py`

Copies the fixture operator into a running container, compiles it, runs inference, and checks output against expected values.

- [ ] **Step 1: Write failing tests**

Create `tests/test_stage_use.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_stage_use.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `stages/stage_use.py`**

```python
import os
import tarfile
import tempfile
import io
import numpy as np
from stages.base import BaseStage
from metrics.collector import MetricsCollector

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "custom_op")
EXPECTED_OUTPUT = [11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0]
TOLERANCE = 1e-5


class UseStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._container = None
        self._compile_errors = 0
        self._compile_warnings = 0
        self._run_errors = 0

    def setup(self) -> None:
        pass  # Container injected by runner from GetStage

    def run(self) -> None:
        self._copy_fixtures()

        self._mc.start("compile")
        result = self._container.exec_run("bash /op/build.sh", workdir="/op")
        self._mc.stop("compile")

        output = result.output.decode("utf-8", errors="replace")
        if result.exit_code != 0 or "BUILD_SUCCESS" not in output:
            self._compile_errors = output.lower().count("error:")
            self._mc.add_error("compile_failed")
            self._mc.set_fail()
            return
        self._compile_warnings = output.lower().count("warning:")

        self._mc.start("run")
        run_result = self._container.exec_run("python run.py", workdir="/op")
        self._mc.stop("run")

        if run_result.exit_code != 0:
            self._run_errors += 1
            self._mc.add_error("run_failed")
            self._mc.set_fail()
            return

        self._verify_output(run_result.output.decode().strip())

    def _copy_fixtures(self) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            tar.add(FIXTURE_DIR, arcname="op")
        buf.seek(0)
        self._container.put_archive("/", buf)

    def _verify_output(self, raw: str) -> None:
        try:
            values = [float(v) for v in raw.split(",")]
            for got, want in zip(values, EXPECTED_OUTPUT):
                if abs(got - want) >= TOLERANCE:
                    self._mc.add_error(f"output_mismatch: got {got}, want {want}")
                    self._mc.set_fail()
                    return
        except Exception as e:
            self._mc.add_error(f"output_parse_error: {e}")
            self._mc.set_fail()

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        pass

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "compile_s": self._mc.elapsed("compile"),
            "run_s": self._mc.elapsed("run"),
            "compile_errors": self._compile_errors,
            "compile_warnings": self._compile_warnings,
            "run_errors": self._run_errors,
        })
        return d
```

- [ ] **Step 4: Run to verify pass**

```bash
pytest tests/test_stage_use.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add stages/stage_use.py tests/test_stage_use.py
git commit -m "feat: add UseStage (compile AiCPU op, run, verify output)"
```

---

## Task 10: Stage 4 — Contribute

**Files:**
- Create: `stages/stage_contribute.py`
- Test: `tests/test_stage_contribute.py`

Submits a test Issue and PR to the CANN Gitcode repository, polls for Issue first-response and PR CI timing.

- [ ] **Step 1: Write failing tests**

Create `tests/test_stage_contribute.py`:

```python
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
    with patch("stages.stage_contribute.requests") as mock_req:
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
    with patch("stages.stage_contribute.requests") as mock_req:
        mock_req.post.return_value = MagicMock(status_code=401, json=MagicMock(return_value={}))
        stage.setup()
        stage.run_issue()
        m = stage.metrics()
        assert m["issue"]["status"] == "fail"

def test_pr_ci_metrics_recorded():
    stage = ContributeStage(CONFIG)
    with patch("stages.stage_contribute.requests") as mock_req, \
         patch("stages.stage_contribute.git") as mock_git:
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
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_stage_contribute.py -v
```

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `stages/stage_contribute.py`**

```python
import time
import datetime
import requests
import git
from stages.base import BaseStage
from metrics.collector import MetricsCollector

GITCODE_API = "https://gitcode.com/api/v4"


class ContributeStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._token = config.get("gitcode_token", "")
        self._fork = config.get("fork_repo", "")
        self._upstream = config.get("upstream_repo", "")
        self._timeouts = config.get("timeout", {})
        self._issue_mc = MetricsCollector()
        self._pr_mc = MetricsCollector()
        self._pr_ci_fields: dict = {}

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    def setup(self) -> None:
        pass

    def run(self) -> None:
        self.run_issue()
        self.run_pr()

    def run_issue(self) -> None:
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        payload = {
            "title": f"[TTFHW-TEST] Automated test issue {ts}",
            "description": "This is an automated TTFHW test issue. Please ignore.",
        }
        self._issue_mc.start("submit")
        resp = requests.post(
            f"{GITCODE_API}/projects/{self._upstream.replace('/', '%2F')}/issues",
            json=payload,
            headers=self._headers(),
        )
        self._issue_mc.stop("submit")

        if resp.status_code != 201:
            self._issue_mc.add_error(f"issue_create_failed: HTTP {resp.status_code}")
            self._issue_mc.set_fail()
            return

        issue_iid = resp.json().get("iid")
        self._poll_issue_response(issue_iid)

    def _poll_issue_response(self, issue_iid: int) -> None:
        timeout = self._timeouts.get("issue_response_s", 3600)
        deadline = time.monotonic() + timeout
        response_start = time.monotonic()
        first_response_s = None
        project = self._upstream.replace("/", "%2F")

        while time.monotonic() < deadline:
            r = requests.get(
                f"{GITCODE_API}/projects/{project}/issues/{issue_iid}/notes",
                headers=self._headers(),
            )
            comments = r.json()
            if comments:
                first_response_s = round(time.monotonic() - response_start, 3)
                break
            time.sleep(30)

        # null on timeout (spec requirement), warn status
        self._issue_mc._extras = getattr(self._issue_mc, "_extras", {})
        self._issue_mc._extras["first_response_s"] = first_response_s
        if first_response_s is None:
            self._issue_mc.set_warn()

    def run_pr(self) -> None:
        ts = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        branch = f"ttfhw-test-{ts}"

        # Push fixture to fork
        try:
            repo = git.Repo.clone_from(
                f"https://oauth2:{self._token}@gitcode.com/{self._fork}.git",
                f"/tmp/ttfhw-fork-{ts}",
            )
            repo.git.checkout("-b", branch)
            # Copy fixtures is handled externally; here we create a dummy commit
            open(f"{repo.working_dir}/ttfhw_test_{ts}.txt", "w").write("TTFHW test")
            repo.git.add(A=True)
            repo.index.commit(f"[TTFHW-TEST] Test operator contribution {ts}")
            repo.remote("origin").push(branch)
        except Exception as e:
            self._pr_mc.add_error(f"fork_push_failed: {e}")
            self._pr_mc.set_fail()
            return

        payload = {
            "source_branch": branch,
            "target_branch": "master",
            "title": f"[TTFHW-TEST] Automated test PR {ts}",
            "description": "Automated TTFHW test PR. Please ignore.",
            "source_project_id": self._fork,
        }
        self._pr_mc.start("submit")
        resp = requests.post(
            f"{GITCODE_API}/projects/{self._upstream.replace('/', '%2F')}/merge_requests",
            json=payload,
            headers=self._headers(),
        )
        self._pr_mc.stop("submit")

        if resp.status_code != 201:
            self._pr_mc.add_error(f"pr_create_failed: HTTP {resp.status_code}")
            self._pr_mc.set_fail()
            return

        mr_iid = resp.json().get("iid")
        self._poll_ci(mr_iid)

    def _poll_ci(self, mr_iid: int) -> None:
        timeout = self._timeouts.get("ci_total_s", 7200)
        deadline = time.monotonic() + timeout
        self._pr_mc.start("ci_total")
        ci_queue_start = time.monotonic()
        ci_prepare_start = ci_run_start = None
        ci_result = "timeout"
        project = self._upstream.replace("/", "%2F")

        while time.monotonic() < deadline:
            r = requests.get(
                f"{GITCODE_API}/projects/{project}/merge_requests/{mr_iid}/pipelines",
                headers=self._headers(),
            )
            pipelines = r.json()
            if not pipelines:
                time.sleep(60)
                continue

            pipeline = pipelines[0]
            status = pipeline.get("status", "")

            if ci_prepare_start is None and status == "running":
                ci_prepare_start = time.monotonic()
                self._pr_ci_fields["ci_queue_s"] = round(ci_prepare_start - ci_queue_start, 3)

            if ci_run_start is None and ci_prepare_start and status == "running":
                # NOTE: ci_prepare_s requires job-level log parsing to measure accurately.
                # In this version, ci_prepare_s is recorded as 0.0 (a known limitation).
                # To implement properly: poll the pipeline's jobs list, find when the first
                # job transitions from "pending" to "running", then watch its log stream
                # for the first test output line.
                ci_run_start = ci_prepare_start
                self._pr_ci_fields["ci_prepare_s"] = 0.0  # Known limitation: v1 approximation

            if status in ("success", "failed", "canceled"):
                ci_end = time.monotonic()
                if ci_run_start:
                    self._pr_ci_fields["ci_run_s"] = round(ci_end - ci_run_start, 3)
                ci_result = status
                break

            time.sleep(60)

        self._pr_mc.stop("ci_total")
        self._pr_ci_fields["ci_total_s"] = self._pr_mc.elapsed("ci_total")
        self._pr_ci_fields["ci_result"] = ci_result
        if ci_result == "timeout":
            self._pr_mc.set_warn()

    def verify(self) -> bool:
        return self._issue_mc.status() != "fail" and self._pr_mc.status() != "fail"

    def teardown(self) -> None:
        pass

    def metrics(self) -> dict:
        issue_d = self._issue_mc.to_dict()
        issue_d["submit_s"] = self._issue_mc.elapsed("submit")
        # first_response_s is null on timeout (stored in _extras, not via elapsed)
        issue_d["first_response_s"] = getattr(self._issue_mc, "_extras", {}).get("first_response_s")

        pr_d = self._pr_mc.to_dict()
        pr_d["submit_s"] = self._pr_mc.elapsed("submit")
        pr_d.update(self._pr_ci_fields)

        return {"issue": issue_d, "pr_ci": pr_d}
```

- [ ] **Step 4: Run to verify pass**

```bash
pytest tests/test_stage_contribute.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add stages/stage_contribute.py tests/test_stage_contribute.py
git commit -m "feat: add ContributeStage (Issue submit + PR CI tracking)"
```

---

## Task 11: Wire Runner with Real Stages

**Files:**
- Modify: `runner.py`

Update `runner.py` to load config from `config.yaml` and instantiate real stage objects. Add a CLI entry point.

- [ ] **Step 1: Update `runner.py` with config loading and CLI**

Add to bottom of `runner.py`:

```python
import sys
import json
import yaml
from stages.stage_learn import LearnStage
from stages.stage_get import GetStage
from stages.stage_use import UseStage
from stages.stage_contribute import ContributeStage
from reports.reporter import Reporter


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        raw = yaml.safe_load(f)
    # Expand environment variables in token
    import os
    token = raw.get("gitcode_token", "")
    if token.startswith("${") and token.endswith("}"):
        env_var = token[2:-1]
        raw["gitcode_token"] = os.environ.get(env_var, "")
    return raw


def build_runner(config: dict) -> "Runner":
    stages = {
        "learn": LearnStage(config),
        "get": GetStage(config),
        "use": UseStage(config),
        "contribute": ContributeStage(config),
    }
    return Runner(stages=stages, config=config)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CANN TTFHW Test Runner")
    parser.add_argument("--stages", nargs="*",
                        default=["learn", "get", "use", "contribute"],
                        help="Stages to run")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    runner = build_runner(config)
    report = runner.run(args.stages)
    reporter = Reporter(report)

    if args.format == "json":
        print(json.dumps(reporter.to_json(), indent=2, ensure_ascii=False))
    else:
        print(reporter.to_markdown())
```

- [ ] **Step 2: Run existing tests to confirm nothing is broken**

```bash
pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add runner.py
git commit -m "feat: wire runner with real stages and add CLI entry point"
```

---

## Task 12: MCP Server

**Files:**
- Create: `mcp_server.py`

Exposes three MCP tools: `cann_ttfhw_run_all`, `cann_ttfhw_run_stage`, `cann_ttfhw_report`. Stores the last run's report in memory for `report` calls.

- [ ] **Step 1: Implement `mcp_server.py`**

```python
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from runner import load_config, build_runner
from reports.reporter import Reporter

app = Server("cann-ttfhw")
_last_report: dict | None = None
_config = load_config()


@app.tool()
async def cann_ttfhw_run_all() -> list[types.TextContent]:
    """Run all four TTFHW stages and return a full report."""
    global _last_report
    runner = build_runner(_config)
    _last_report = runner.run(["learn", "get", "use", "contribute"])
    reporter = Reporter(_last_report)
    return [types.TextContent(type="text", text=reporter.to_markdown())]


@app.tool()
async def cann_ttfhw_run_stage(
    stage: str,
    substage: str | None = None,
) -> list[types.TextContent]:
    """Run a single TTFHW stage. stage: learn|get|use|contribute. substage (contribute only): issue|pr_ci."""
    global _last_report
    runner = build_runner(_config)
    if stage == "contribute" and substage:
        from stages.stage_contribute import ContributeStage
        c = ContributeStage(_config)
        c.setup()
        if substage == "issue":
            c.run_issue()
        elif substage == "pr_ci":
            c.run_pr()
        result = {"stages": {"contribute": c.metrics()}}
    else:
        result = runner.run([stage])
    _last_report = result
    reporter = Reporter(result)
    return [types.TextContent(type="text", text=reporter.to_markdown())]


@app.tool()
async def cann_ttfhw_report(format: str = "markdown") -> list[types.TextContent]:
    """Return the latest TTFHW test report. format: json|markdown."""
    if _last_report is None:
        return [types.TextContent(type="text", text="No report available. Run cann_ttfhw_run_all first.")]
    reporter = Reporter(_last_report)
    if format == "json":
        return [types.TextContent(type="text", text=json.dumps(reporter.to_json(), indent=2, ensure_ascii=False))]
    return [types.TextContent(type="text", text=reporter.to_markdown())]


if __name__ == "__main__":
    import asyncio
    asyncio.run(stdio_server(app))
```

- [ ] **Step 2: Verify MCP server starts without error**

```bash
python mcp_server.py --help 2>&1 | head -5 || echo "started ok"
```

- [ ] **Step 3: Commit**

```bash
git add mcp_server.py
git commit -m "feat: add MCP server with run_all, run_stage, report tools"
```

---

## Task 13: Claude Skill Definitions

**Files:**
- Create: `skills/cann-ttfhw.md`
- Create: `skills/cann-learn.md`
- Create: `skills/cann-get.md`
- Create: `skills/cann-use.md`
- Create: `skills/cann-contribute.md`
- Create: `skills/cann-contribute-issue.md`
- Create: `skills/cann-contribute-pr.md`

Each skill file tells Claude Code which MCP tool to call.

- [ ] **Step 1: Create skill files**

`skills/cann-ttfhw.md`:
```markdown
---
name: cann-ttfhw
description: Run full CANN TTFHW benchmark (all 4 stages) and display results
---
Call MCP tool `cann_ttfhw_run_all`. Display the returned Markdown report to the user.
```

`skills/cann-learn.md`:
```markdown
---
name: cann-learn
description: Run CANN TTFHW Learn stage only (search → navigate → link check)
---
Call MCP tool `cann_ttfhw_run_stage` with `stage="learn"`. Display results.
```

`skills/cann-get.md`:
```markdown
---
name: cann-get
description: Run CANN TTFHW Get stage only (docker pull → start → verify)
---
Call MCP tool `cann_ttfhw_run_stage` with `stage="get"`. Display results.
```

`skills/cann-use.md`:
```markdown
---
name: cann-use
description: Run CANN TTFHW Use stage only (compile op → run → verify output)
---
Call MCP tool `cann_ttfhw_run_stage` with `stage="use"`. Display results.
```

`skills/cann-contribute.md`:
```markdown
---
name: cann-contribute
description: Run CANN TTFHW Contribute stage (Issue + PR CI tracking)
---
Call MCP tool `cann_ttfhw_run_stage` with `stage="contribute"`. Display results.
```

`skills/cann-contribute-issue.md`:
```markdown
---
name: cann-contribute-issue
description: Run CANN TTFHW Contribute-Issue sub-stage only
---
Call MCP tool `cann_ttfhw_run_stage` with `stage="contribute"` and `substage="issue"`. Display results.
```

`skills/cann-contribute-pr.md`:
```markdown
---
name: cann-contribute-pr
description: Run CANN TTFHW Contribute-PR CI sub-stage only
---
Call MCP tool `cann_ttfhw_run_stage` with `stage="contribute"` and `substage="pr_ci"`. Display results.
```

- [ ] **Step 2: Run full test suite to confirm all tests pass**

```bash
pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 3: Final commit**

```bash
git add skills/
git commit -m "feat: add Claude Skill definitions for all TTFHW commands"
```

---

## Done

All tasks complete when:
- `pytest tests/ -v` — all tests pass
- `python runner.py --format markdown` — runs without import errors (stages will fail without real Docker/Gitcode, which is expected in dev)
- `python mcp_server.py` — server starts without error
- `skills/` directory contains 7 skill definition files
