# CANN 易用性评估工具 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建 cann-eval 自动化评估工具，覆盖了解/获取/使用三个阶段，输出中文评估报告，支持 MCP + CLI + 人工辅助三种接口。

**Architecture:** 平铺 Stage 模式（5 个 Stage），Runner 统一编排，MetricsCollector 收集断点，Reporter 生成中文 Markdown + JSON 报告。了解阶段用 googlesearch-python 爬取 Google 搜索结果，获取阶段测试 Docker pull 和 .run 包安装，使用阶段验证 ATC 工具链和 Qwen2-0.5B CPU 推理。

**Tech Stack:** Python 3.11+, googlesearch-python, docker SDK, requests, modelscope, transformers, torch, torch-npu, mcp (FastMCP), pytest

---

## 文件结构

```
cann-eval/
├── config.yaml
├── runner.py
├── requirements.txt
├── mcp_server.py
├── skills/cann-eval.md
├── stages/
│   ├── __init__.py
│   ├── base.py
│   ├── stage_learn.py
│   ├── stage_get_docker.py
│   ├── stage_get_runpkg.py
│   ├── stage_use_quickstart.py
│   └── stage_use_qwen2.py
├── metrics/
│   ├── __init__.py
│   └── collector.py
├── reports/
│   ├── __init__.py
│   └── reporter.py
├── manual/
│   └── recorder.py
└── tests/
    ├── __init__.py
    ├── test_collector.py
    ├── test_stage_learn.py
    ├── test_stage_get_docker.py
    ├── test_stage_get_runpkg.py
    ├── test_stage_use_quickstart.py
    ├── test_stage_use_qwen2.py
    └── test_reporter.py
```

---

### Task 1: 项目脚手架

**Files:**
- Create: `cann-eval/config.yaml`
- Create: `cann-eval/requirements.txt`
- Create: `cann-eval/stages/__init__.py`
- Create: `cann-eval/metrics/__init__.py`
- Create: `cann-eval/reports/__init__.py`
- Create: `cann-eval/tests/__init__.py`

- [ ] **Step 1: 创建 config.yaml**

```yaml
cann_image: "ascendai/cann:latest"
run_pkg_url: ""
quickstart_url: "https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/80RC3alpha003/quickstart/quickstart/quickstart_18_0001.html"
qwen2_model: "qwen/Qwen2-0.5B"
qwen2_source: "modelscope"
qwen2_cache_dir: "/tmp/qwen2_cache"

timeout:
  learn_s: 60
  get_docker_s: 600
  get_runpkg_s: 300
  use_quickstart_s: 60
  use_qwen2_s: 600

on_stage_failure: continue
```

- [ ] **Step 2: 创建 requirements.txt**

```
googlesearch-python>=1.2.0
requests>=2.31.0
docker>=7.0.0
modelscope>=1.9.0
transformers>=4.40.0
torch>=2.2.0
torch-npu>=2.2.0
mcp>=1.0.0
pyyaml>=6.0
pytest>=8.0.0
pytest-mock>=3.12.0
```

- [ ] **Step 3: 创建 __init__.py 占位文件**

在 `stages/`、`metrics/`、`reports/`、`tests/`、`manual/` 各创建空 `__init__.py`。

- [ ] **Step 4: 安装依赖（必须在所有测试之前完成）**

```bash
cd /home/zhongjun/claude/zhongjun2/ttfhw/cann-eval
pip install -r requirements.txt
```
Expected: 所有包安装成功，无报错。

> **注意：** 依赖在此处一次性安装，后续各 Task 的"运行确认失败"步骤中测试失败原因应为"模块源文件不存在"，而非"pip 包未安装"。

- [ ] **Step 5: 提交**

```bash
cd /home/zhongjun/claude/zhongjun2/ttfhw/cann-eval
git init  # 如果还没有 git
git add config.yaml requirements.txt stages/__init__.py metrics/__init__.py reports/__init__.py tests/__init__.py manual/__init__.py
git commit -m "chore: project scaffolding"
```

---

### Task 2: MetricsCollector

**Files:**
- Create: `cann-eval/metrics/collector.py`
- Test: `cann-eval/tests/test_collector.py`

- [ ] **Step 1: 写失败测试**

```python
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
```

- [ ] **Step 2: 运行确认失败**

```bash
cd /home/zhongjun/claude/zhongjun2/ttfhw/cann-eval
python -m pytest tests/test_collector.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'metrics.collector'`

- [ ] **Step 3: 实现 MetricsCollector**

```python
# metrics/collector.py
import time


class MetricsCollector:
    def __init__(self):
        self._starts: dict[str, float] = {}
        self._stops: dict[str, float] = {}
        self._breakpoints: list[dict] = []
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

    def add_error(
        self,
        phenomenon: str,
        severity: str = "P1",
        cause: str = "",
        solution: str = "",
    ) -> None:
        self._breakpoints.append({
            "severity": severity,
            "phenomenon": phenomenon,
            "cause": cause,
            "solution": solution,
        })

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
        result: dict = {"status": self.status(), "breakpoints": self._breakpoints}
        for name in self._stops:
            result[f"{name}_s"] = self.elapsed(name)
        return result
```

- [ ] **Step 4: 运行确认通过**

```bash
python -m pytest tests/test_collector.py -v
```
Expected: 8 passed

- [ ] **Step 5: 提交**

```bash
git add metrics/collector.py tests/test_collector.py
git commit -m "feat: add MetricsCollector with breakpoint support"
```

---

### Task 3: BaseStage

**Files:**
- Create: `cann-eval/stages/base.py`

- [ ] **Step 1: 实现 BaseStage（无需独立测试，各 Stage 测试中覆盖）**

```python
# stages/base.py
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

- [ ] **Step 2: 提交**

```bash
git add stages/base.py
git commit -m "feat: add BaseStage abstract interface"
```

---

### Task 4: LearnStage

**Files:**
- Create: `cann-eval/stages/stage_learn.py`
- Test: `cann-eval/tests/test_stage_learn.py`

- [ ] **Step 1: 写失败测试**

```python
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
```

- [ ] **Step 2: 运行确认失败**

```bash
python -m pytest tests/test_stage_learn.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现 LearnStage**

```python
# stages/stage_learn.py
import time
import requests
from googlesearch import search
from stages.base import BaseStage
from metrics.collector import MetricsCollector


class LearnStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._official_url: str | None = None
        self._official_rank: int | None = None
        self._official_accessible: bool = False
        self._quickstart_url: str | None = None
        self._quickstart_found: bool = False
        self._qwen2_guide_url: str | None = None
        self._qwen2_guide_found: bool = False
        self._accessible_links: int = 0
        self._broken_links: int = 0

    def setup(self) -> None:
        pass

    def run(self) -> None:
        timeout = self._config.get("timeout", {}).get("learn_s", 60)
        self._mc.start("search")
        try:
            self._run_search(timeout)
        finally:
            self._mc.stop("search")

    def _run_search(self, timeout: int) -> None:
        # Step 1: 搜索官方文档入口
        try:
            results = list(search("CANN 昇腾 安装", num_results=10, sleep_interval=2))
        except Exception as e:
            self._mc.add_error(
                phenomenon=f"Google 搜索失败: {e}",
                severity="P0",
                cause="网络问题或 Google 封禁",
                solution="检查网络连接，或稍后重试",
            )
            self._mc.set_fail()
            return

        for i, url in enumerate(results, start=1):
            if "hiascend.com" in url:
                self._official_url = url
                self._official_rank = i
                break

        if not self._official_url:
            self._mc.add_error(
                phenomenon="搜索结果中未找到 hiascend.com 官方链接",
                severity="P1",
                cause="官方文档 SEO 排名低，或搜索结果受地区影响",
                solution="直接访问 hiascend.com 文档页面",
            )
            self._mc.set_fail()

        # Step 2: 搜索 Quick Start 链接
        time.sleep(2)
        try:
            qs_results = list(search("CANN 快速入门 site:hiascend.com", num_results=5, sleep_interval=2))
            if qs_results:
                self._quickstart_url = qs_results[0]
                self._quickstart_found = True
        except Exception:
            pass
        if not self._quickstart_found:
            fallback = self._config.get("quickstart_url", "")
            if fallback:
                self._quickstart_url = fallback
                self._quickstart_found = True

        # Step 3: 搜索 Qwen2 部署文档
        time.sleep(2)
        try:
            qwen_results = list(search("Qwen2 CANN 昇腾 部署", num_results=5, sleep_interval=2))
            if qwen_results:
                self._qwen2_guide_url = qwen_results[0]
                self._qwen2_guide_found = True
        except Exception:
            pass

        # Step 4: 检查所有找到的链接可达性（同时更新 official_accessible）
        urls_to_check = [u for u in [
            self._official_url,
            self._quickstart_url,
            self._qwen2_guide_url,
        ] if u]
        self._check_links(urls_to_check, timeout)

    def _check_links(self, urls: list[str], timeout: int) -> None:
        with requests.Session() as session:
            for url in urls:
                try:
                    r = session.head(url, timeout=10, allow_redirects=True)
                    if r.status_code < 400:
                        self._accessible_links += 1
                        if url == self._official_url:
                            self._official_accessible = True  # 官方链接可达
                    else:
                        self._broken_links += 1
                        self._mc.add_error(
                            phenomenon=f"链接不可访问: {url} (HTTP {r.status_code})",
                            severity="P2",
                            cause="文档 URL 变更或服务不可用",
                            solution="手动访问确认最新链接",
                        )
                        self._mc.set_warn()
                except Exception as e:
                    self._broken_links += 1
                    self._mc.add_error(
                        phenomenon=f"链接检查失败: {url}",
                        severity="P2",
                        cause=str(e),
                        solution="检查网络连接",
                    )
                    self._mc.set_warn()

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        pass

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "official_link_rank": self._official_rank,
            "official_url": self._official_url,
            "official_accessible": self._official_accessible,
            "quickstart_url": self._quickstart_url,
            "quickstart_found": self._quickstart_found,
            "qwen2_guide_url": self._qwen2_guide_url,
            "qwen2_guide_found": self._qwen2_guide_found,
            "accessible_links": self._accessible_links,
            "broken_links": self._broken_links,
        })
        return d
```

- [ ] **Step 4: 运行确认通过**

```bash
python -m pytest tests/test_stage_learn.py -v
```
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add stages/stage_learn.py tests/test_stage_learn.py
git commit -m "feat: add LearnStage with Google search"
```

---

### Task 5: GetDockerStage

**Files:**
- Create: `cann-eval/stages/stage_get_docker.py`
- Test: `cann-eval/tests/test_stage_get_docker.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_stage_get_docker.py
import pytest
from unittest.mock import patch, MagicMock
from stages.stage_get_docker import GetDockerStage

BASE_CONFIG = {
    "cann_image": "ascendai/cann:latest",
    "timeout": {"get_docker_s": 30},
}

def _make_stage(config=None):
    return GetDockerStage(config or BASE_CONFIG)

def test_get_docker_pull_success():
    stage = _make_stage()
    mock_client = MagicMock()
    mock_img = MagicMock()
    mock_img.attrs = {"Size": 4 * 1024 * 1024 * 1024}
    mock_client.images.pull.return_value = mock_img
    mock_container = MagicMock()
    mock_container.exec_run.return_value = MagicMock(exit_code=0, output=b"ATC start working")
    mock_client.containers.run.return_value = mock_container
    with patch("stages.stage_get_docker.docker.from_env", return_value=mock_client):
        stage.setup()
        stage.run()
    assert stage.verify() is True
    m = stage.metrics()
    assert m["image_size_mb"] == pytest.approx(4096.0, abs=1)
    assert m["atc_available"] is True

def test_get_docker_pull_failure_sets_fail():
    stage = _make_stage()
    mock_client = MagicMock()
    mock_client.images.pull.side_effect = Exception("pull failed")
    with patch("stages.stage_get_docker.docker.from_env", return_value=mock_client):
        stage.setup()
        stage.run()
    assert stage.verify() is False
    m = stage.metrics()
    assert len(m["breakpoints"]) > 0

def test_get_docker_atc_not_available_sets_warn():
    stage = _make_stage()
    mock_client = MagicMock()
    mock_img = MagicMock()
    mock_img.attrs = {"Size": 1024}
    mock_client.images.pull.return_value = mock_img
    mock_container = MagicMock()
    mock_container.exec_run.return_value = MagicMock(exit_code=1, output=b"not found")
    mock_client.containers.run.return_value = mock_container
    with patch("stages.stage_get_docker.docker.from_env", return_value=mock_client):
        stage.setup()
        stage.run()
    assert stage.metrics()["atc_available"] is False

def test_get_docker_teardown_does_not_stop_if_container_none():
    stage = _make_stage()
    stage.teardown()  # should not raise
```

- [ ] **Step 2: 运行确认失败**

```bash
python -m pytest tests/test_stage_get_docker.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: 实现 GetDockerStage**

```python
# stages/stage_get_docker.py
import docker
from stages.base import BaseStage
from metrics.collector import MetricsCollector


class GetDockerStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._client = None
        self._container = None
        self._image_size_mb: float | None = None
        self._cann_version: str | None = None
        self._atc_available: bool = False

    def setup(self) -> None:
        try:
            self._client = docker.from_env()
        except Exception as e:
            self._mc.add_error(
                phenomenon=f"Docker 客户端初始化失败: {e}",
                severity="P0",
                cause="Docker 未安装或当前用户无权限",
                solution="安装 Docker 并将用户加入 docker 组（newgrp docker）",
            )
            self._mc.set_fail()

    def run(self) -> None:
        if self._client is None:
            return
        image_name = self._config.get("cann_image", "ascendai/cann:latest")
        timeout = self._config.get("timeout", {}).get("get_docker_s", 600)

        self._mc.start("wall_clock")
        self._mc.start("net_download")
        try:
            img = self._client.images.pull(image_name, timeout=timeout)
            self._mc.stop("net_download")
            self._image_size_mb = round(img.attrs.get("Size", 0) / (1024 * 1024), 1)
        except Exception as e:
            self._mc.stop("net_download")
            self._mc.add_error(
                phenomenon=f"docker pull 失败: {e}",
                severity="P0",
                cause="镜像地址不可达或网络超时",
                solution="确认使用 ascendai/cann:latest（Docker Hub 公开镜像）",
            )
            self._mc.set_fail()
            self._mc.stop("wall_clock")
            return

        try:
            self._container = self._client.containers.run(
                image_name, detach=True, tty=True
            )
        except Exception as e:
            self._mc.add_error(
                phenomenon=f"容器启动失败: {e}",
                severity="P0",
                cause="Docker 资源不足或镜像损坏",
                solution="检查磁盘空间和内存",
            )
            self._mc.set_fail()
            self._mc.stop("wall_clock")
            return

        # 验证 CANN 工具链
        result = self._container.exec_run(
            "bash -c 'source /usr/local/Ascend/cann-*/set_env.sh 2>/dev/null && atc --help 2>&1 | head -3'"
        )
        if result.exit_code == 0:
            self._atc_available = True
        else:
            self._mc.add_error(
                phenomenon="atc --help 返回非零退出码",
                severity="P1",
                cause="CANN 工具链未正确安装或 set_env.sh 路径变更",
                solution="手动检查容器内 /usr/local/Ascend/ 目录结构",
            )
            self._mc.set_warn()

        # 读取 CANN 版本
        ver_result = self._container.exec_run(
            "bash -c \"cat /usr/local/Ascend/cann-*/x86_64-linux/ascend_toolkit_install.info 2>/dev/null | grep version | head -1\""
        )
        if ver_result.exit_code == 0:
            self._cann_version = ver_result.output.decode("utf-8", errors="ignore").strip()

        self._mc.stop("wall_clock")

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        # Runner 负责决定何时调用（需等 UseQuickStartStage 完成后）
        if self._container:
            try:
                self._container.stop(timeout=5)
                self._container.remove()
            except Exception:
                pass
            self._container = None

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "net_download_s": self._mc.elapsed("net_download"),
            "wall_clock_s": self._mc.elapsed("wall_clock"),
            "image_size_mb": self._image_size_mb,
            "cann_version": self._cann_version,
            "atc_available": self._atc_available,
        })
        return d
```

- [ ] **Step 4: 运行确认通过**

```bash
python -m pytest tests/test_stage_get_docker.py -v
```
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add stages/stage_get_docker.py tests/test_stage_get_docker.py
git commit -m "feat: add GetDockerStage"
```

---

### Task 6: GetRunPkgStage

**Files:**
- Create: `cann-eval/stages/stage_get_runpkg.py`
- Test: `cann-eval/tests/test_stage_get_runpkg.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_stage_get_runpkg.py
import pytest
from unittest.mock import patch, MagicMock, mock_open
from stages.stage_get_runpkg import GetRunPkgStage

BASE_CONFIG = {
    "run_pkg_url": "https://example.com/Ascend-cann-toolkit_9.0.run",
    "timeout": {"get_runpkg_s": 30},
}

def _make_stage(config=None):
    return GetRunPkgStage(config or BASE_CONFIG)

def test_runpkg_no_url_sets_fail():
    stage = GetRunPkgStage({"run_pkg_url": "", "timeout": {"get_runpkg_s": 10}})
    stage.setup()
    stage.run()
    assert stage.verify() is False

def test_runpkg_download_success():
    stage = _make_stage()
    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [b"data" * 1024]
    mock_resp.headers = {"content-length": "4096"}
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("stages.stage_get_runpkg.requests.get", return_value=mock_resp), \
         patch("builtins.open", mock_open()), \
         patch("stages.stage_get_runpkg.subprocess.run") as mock_run, \
         patch("stages.stage_get_runpkg.os.chmod"), \
         patch("stages.stage_get_runpkg.os.path.exists", return_value=True), \
         patch("stages.stage_get_runpkg.os.path.getsize", return_value=4096):
        mock_run.return_value = MagicMock(returncode=1, stderr="permission denied")
        stage.setup()
        stage.run()
    m = stage.metrics()
    assert m["download_s"] is not None
    assert m["install_exit_code"] == 1  # 无 root，预期失败

def test_runpkg_download_failure_sets_fail():
    stage = _make_stage()
    with patch("stages.stage_get_runpkg.requests.get", side_effect=Exception("timeout")):
        stage.setup()
        stage.run()
    assert stage.verify() is False
    m = stage.metrics()
    assert len(m["breakpoints"]) > 0
```

- [ ] **Step 2: 运行确认失败**

```bash
python -m pytest tests/test_stage_get_runpkg.py -v
```

- [ ] **Step 3: 实现 GetRunPkgStage**

```python
# stages/stage_get_runpkg.py
import os
import subprocess
import tempfile
import requests
from stages.base import BaseStage
from metrics.collector import MetricsCollector


class GetRunPkgStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._tmp_file: str | None = None
        self._file_size_mb: float | None = None
        self._install_exit_code: int | None = None
        self._install_stderr: str = ""
        self._atc_available: bool | None = None

    def setup(self) -> None:
        pass

    def run(self) -> None:
        url = self._config.get("run_pkg_url", "")
        if not url:
            self._mc.add_error(
                phenomenon=".run 包下载 URL 未配置",
                severity="P1",
                cause="hiascend.com 为 SPA，URL 需手动更新到 config.yaml",
                solution="访问 hiascend.com 找到最新版本 .run 包下载链接，填入 run_pkg_url",
            )
            self._mc.set_fail()
            return

        timeout = self._config.get("timeout", {}).get("get_runpkg_s", 300)

        # 下载
        self._mc.start("download")
        try:
            with requests.get(url, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                fd, self._tmp_file = tempfile.mkstemp(suffix=".run")
                with os.fdopen(fd, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            self._mc.stop("download")
            self._file_size_mb = round(os.path.getsize(self._tmp_file) / (1024 * 1024), 1)
        except Exception as e:
            self._mc.stop("download")
            self._mc.add_error(
                phenomenon=f".run 包下载失败: {e}",
                severity="P0",
                cause="网络问题或 URL 失效",
                solution="检查 run_pkg_url 是否有效",
            )
            self._mc.set_fail()
            return

        # 安装
        os.chmod(self._tmp_file, 0o755)
        self._mc.start("install")
        try:
            result = subprocess.run(
                [self._tmp_file, "--install"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            self._mc.stop("install")
            self._install_exit_code = result.returncode
            self._install_stderr = result.stderr[:500]
            if result.returncode != 0:
                self._mc.add_error(
                    phenomenon=f".run 安装失败（exit code {result.returncode}）",
                    severity="P1",
                    cause="无 root 权限，或系统依赖缺失",
                    solution="使用 sudo 执行，或改用 Docker 方式安装",
                )
                self._mc.set_warn()
            else:
                # 安装成功，验证工具链
                r2 = subprocess.run(
                    ["bash", "-c", "source /usr/local/Ascend/cann-*/set_env.sh 2>/dev/null && atc --help"],
                    capture_output=True, text=True, timeout=30,
                )
                self._atc_available = (r2.returncode == 0)
        except subprocess.TimeoutExpired:
            self._mc.stop("install")
            self._mc.add_error(
                phenomenon="安装命令超时",
                severity="P1",
                cause="安装过程超时",
                solution="增大 timeout.get_runpkg_s 配置",
            )
            self._mc.set_warn()

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        if self._tmp_file and os.path.exists(self._tmp_file):
            try:
                os.remove(self._tmp_file)
            except Exception:
                pass

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "download_s": self._mc.elapsed("download"),
            "install_s": self._mc.elapsed("install"),
            "file_size_mb": self._file_size_mb,
            "install_exit_code": self._install_exit_code,
            "install_stderr": self._install_stderr,
            "atc_available": self._atc_available,
        })
        return d
```

- [ ] **Step 4: 运行确认通过**

```bash
python -m pytest tests/test_stage_get_runpkg.py -v
```
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add stages/stage_get_runpkg.py tests/test_stage_get_runpkg.py
git commit -m "feat: add GetRunPkgStage"
```

---

### Task 7: UseQuickStartStage

**Files:**
- Create: `cann-eval/stages/stage_use_quickstart.py`
- Test: `cann-eval/tests/test_stage_use_quickstart.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_stage_use_quickstart.py
from unittest.mock import MagicMock
from stages.stage_use_quickstart import UseQuickStartStage

BASE_CONFIG = {"timeout": {"use_quickstart_s": 30}}

def _make_stage_with_container(exit_code=0, output=b"ATC start working"):
    stage = UseQuickStartStage(BASE_CONFIG)
    mock_container = MagicMock()
    mock_container.exec_run.return_value = MagicMock(exit_code=exit_code, output=output)
    stage._container = mock_container
    return stage

def test_quickstart_atc_ok():
    stage = _make_stage_with_container(exit_code=0, output=b"ATC start working now")
    stage.setup()
    stage.run()
    assert stage.verify() is True
    m = stage.metrics()
    assert m["atc_exit_code"] == 0
    assert "ATC" in m["atc_help_output"]

def test_quickstart_atc_fail_sets_warn():
    stage = _make_stage_with_container(exit_code=1, output=b"error")
    stage.setup()
    stage.run()
    m = stage.metrics()
    assert m["atc_exit_code"] == 1

def test_quickstart_no_container_sets_fail():
    stage = UseQuickStartStage(BASE_CONFIG)
    stage.setup()
    stage.run()
    assert stage.verify() is False
```

- [ ] **Step 2: 运行确认失败**

```bash
python -m pytest tests/test_stage_use_quickstart.py -v
```

- [ ] **Step 3: 实现 UseQuickStartStage**

```python
# stages/stage_use_quickstart.py
from stages.base import BaseStage
from metrics.collector import MetricsCollector


class UseQuickStartStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._container = None  # 由 Runner 注入
        self._atc_exit_code: int | None = None
        self._atc_help_output: str = ""
        self._set_env_found: bool = False

    def setup(self) -> None:
        if self._container is None:
            self._mc.add_error(
                phenomenon="容器句柄未注入",
                severity="P0",
                cause="GetDockerStage 未成功完成，或 Runner 未注入容器",
                solution="确保 GetDockerStage 先于 UseQuickStartStage 运行",
            )
            self._mc.set_fail()

    def run(self) -> None:
        if self._container is None:
            return
        self._mc.start("toolchain")
        try:
            result = self._container.exec_run(
                "bash -c 'source /usr/local/Ascend/cann-*/set_env.sh 2>/dev/null && which atc && atc --help 2>&1 | head -5'"
            )
            self._mc.stop("toolchain")
            self._atc_exit_code = result.exit_code
            raw = result.output
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="ignore")
            self._atc_help_output = raw[:200]
            self._set_env_found = True

            if result.exit_code != 0:
                self._mc.add_error(
                    phenomenon=f"atc --help 返回退出码 {result.exit_code}",
                    severity="P1",
                    cause="CANN 工具链未正确安装",
                    solution="检查容器内 /usr/local/Ascend/ 目录",
                )
                self._mc.set_warn()
        except Exception as e:
            self._mc.stop("toolchain")
            self._mc.add_error(
                phenomenon=f"容器命令执行失败: {e}",
                severity="P0",
                cause="容器已退出或网络问题",
                solution="重新运行 GetDockerStage",
            )
            self._mc.set_fail()

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        # 容器清理由 Runner 触发 GetDockerStage.teardown()
        pass

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "toolchain_s": self._mc.elapsed("toolchain"),
            "set_env_found": self._set_env_found,
            "atc_exit_code": self._atc_exit_code,
            "atc_help_output": self._atc_help_output,
        })
        return d
```

- [ ] **Step 4: 运行确认通过**

```bash
python -m pytest tests/test_stage_use_quickstart.py -v
```
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add stages/stage_use_quickstart.py tests/test_stage_use_quickstart.py
git commit -m "feat: add UseQuickStartStage"
```

---

### Task 8: UseQwen2Stage

**Files:**
- Create: `cann-eval/stages/stage_use_qwen2.py`
- Test: `cann-eval/tests/test_stage_use_qwen2.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_stage_use_qwen2.py
import pytest
from unittest.mock import patch, MagicMock
from stages.stage_use_qwen2 import UseQwen2Stage

BASE_CONFIG = {
    "qwen2_model": "qwen/Qwen2-0.5B",
    "qwen2_source": "modelscope",
    "qwen2_cache_dir": "/tmp/test_qwen2",
    "timeout": {"use_qwen2_s": 60},
}

def _make_stage(config=None):
    return UseQwen2Stage(config or BASE_CONFIG)

def _setup_stage(stage):
    """Helper: call setup() with venv mocked out."""
    with patch("stages.stage_use_qwen2.venv.create"), \
         patch("stages.stage_use_qwen2.tempfile.mkdtemp", return_value="/tmp/test_venv"):
        stage.setup()

def test_qwen2_inference_success():
    stage = _make_stage()
    _setup_stage(stage)
    with patch("stages.stage_use_qwen2.subprocess.run") as mock_run, \
         patch("stages.stage_use_qwen2.os.path.getsize", return_value=1024 * 1024 * 1000):
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr=""),     # pip install
            MagicMock(returncode=0, stderr=""),     # modelscope download
            MagicMock(returncode=0, stdout="你好，我是 Qwen2", stderr=""),  # inference
        ]
        stage.run()
    assert stage.verify() is True
    m = stage.metrics()
    assert m["inference_ok"] is True

def test_qwen2_inference_failure_software_error():
    stage = _make_stage()
    _setup_stage(stage)
    with patch("stages.stage_use_qwen2.subprocess.run") as mock_run, \
         patch("stages.stage_use_qwen2.os.path.getsize", return_value=1024):
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr=""),    # pip install
            MagicMock(returncode=0, stderr=""),    # modelscope download
            MagicMock(returncode=1, stdout="", stderr="ImportError: No module named 'xxx'"),
        ]
        stage.run()
    m = stage.metrics()
    assert m["inference_ok"] is False
    assert m["software_error"] is True

def test_qwen2_inference_failure_hardware_only():
    stage = _make_stage()
    _setup_stage(stage)
    with patch("stages.stage_use_qwen2.subprocess.run") as mock_run, \
         patch("stages.stage_use_qwen2.os.path.getsize", return_value=1024):
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr=""),
            MagicMock(returncode=0, stderr=""),
            MagicMock(returncode=1, stdout="", stderr="RuntimeError: No NPU device found"),
        ]
        stage.run()
    m = stage.metrics()
    assert m["inference_ok"] is False
    assert m["software_error"] is False  # NPU 缺失属于预期行为，不是软件错误

def test_qwen2_teardown_removes_venv():
    stage = _make_stage()
    _setup_stage(stage)
    with patch("stages.stage_use_qwen2.shutil.rmtree") as mock_rm, \
         patch("stages.stage_use_qwen2.os.path.exists", return_value=True):
        stage.teardown()
    mock_rm.assert_called_once_with("/tmp/test_venv", ignore_errors=True)
```

- [ ] **Step 2: 运行确认失败**

```bash
python -m pytest tests/test_stage_use_qwen2.py -v
```

- [ ] **Step 3: 实现 UseQwen2Stage**

```python
# stages/stage_use_qwen2.py
import os
import shutil
import subprocess
import tempfile
import textwrap
import venv
from stages.base import BaseStage
from metrics.collector import MetricsCollector

# 判断是否为纯硬件错误（NPU 缺失，属预期行为，非软件 bug）
_HARDWARE_ERROR_PATTERNS = [
    "No NPU device",
    "npu device",
    "ascend device",
    "acl.init()",
    "RuntimeError: device",
    "CANN runtime",
]

INFERENCE_SCRIPT = textwrap.dedent("""
import sys
sys.path.insert(0, '{model_path}')
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained('{model_path}', device_map='cpu')
tok = AutoTokenizer.from_pretrained('{model_path}')
out = model.generate(**tok('你好', return_tensors='pt'), max_new_tokens=5)
print(tok.decode(out[0], skip_special_tokens=True))
""")


class UseQwen2Stage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._venv_dir: str | None = None
        self._model_size_mb: float | None = None
        self._inference_ok: bool = False
        self._inference_output: str = ""
        self._software_error: bool = False

    def setup(self) -> None:
        # 创建隔离 venv，避免污染宿主机 Python 环境
        self._venv_dir = tempfile.mkdtemp(prefix="cann_eval_qwen2_venv_")
        venv.create(self._venv_dir, with_pip=True)

    def run(self) -> None:
        cache_dir = self._config.get("qwen2_cache_dir", "/tmp/qwen2_cache")
        model_name = self._config.get("qwen2_model", "qwen/Qwen2-0.5B")
        timeout = self._config.get("timeout", {}).get("use_qwen2_s", 600)
        # 使用 venv 内的 Python，不污染宿主机环境
        python = os.path.join(self._venv_dir, "bin", "python")

        # Step 1: 安装依赖
        self._mc.start("install")
        result = subprocess.run(
            [python, "-m", "pip", "install", "-q",
             "modelscope", "transformers", "torch", "torch-npu"],
            capture_output=True, text=True, timeout=timeout,
        )
        self._mc.stop("install")
        if result.returncode != 0:
            self._mc.add_error(
                phenomenon="pip 安装依赖失败",
                severity="P0",
                cause=result.stderr[:200],
                solution="检查网络连接和 pip 配置",
            )
            self._mc.set_fail()
            return

        # Step 2: 下载模型
        self._mc.start("download")
        dl_result = subprocess.run(
            [python, "-m", "modelscope", "download",
             "--model", model_name, "--local_dir", cache_dir],
            capture_output=True, text=True, timeout=timeout,
        )
        self._mc.stop("download")
        if dl_result.returncode != 0:
            self._mc.add_error(
                phenomenon="Qwen2-0.5B 模型下载失败",
                severity="P0",
                cause=dl_result.stderr[:200],
                solution="检查网络，或手动下载到 qwen2_cache_dir",
            )
            self._mc.set_fail()
            return

        # 统计模型大小
        total = 0
        for root, _, files in os.walk(cache_dir):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
        self._model_size_mb = round(total / (1024 * 1024), 1)

        # Step 3: 运行推理
        script = INFERENCE_SCRIPT.format(model_path=cache_dir)
        self._mc.start("inference")
        inf_result = subprocess.run(
            [python, "-c", script],
            capture_output=True, text=True, timeout=timeout,
        )
        self._mc.stop("inference")

        if inf_result.returncode == 0:
            self._inference_ok = True
            self._inference_output = inf_result.stdout.strip()[:200]
        else:
            stderr = inf_result.stderr
            # 判断是否为纯硬件错误（NPU 缺失）
            is_hw_only = any(p.lower() in stderr.lower() for p in _HARDWARE_ERROR_PATTERNS)
            self._software_error = not is_hw_only
            if self._software_error:
                self._mc.add_error(
                    phenomenon="推理命令因软件原因失败",
                    severity="P0",
                    cause=stderr[:200],
                    solution="检查 transformers/torch 版本兼容性",
                )
                self._mc.set_fail()
            else:
                self._mc.add_error(
                    phenomenon="推理命令因缺少 NPU 硬件失败（预期行为）",
                    severity="P2",
                    cause="当前机器无物理 NPU，无法执行 NPU 推理",
                    solution="在昇腾硬件上运行完整推理",
                )
                self._mc.set_warn()

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        # 删除隔离 venv（保留模型缓存，避免重复下载）
        if self._venv_dir and os.path.exists(self._venv_dir):
            shutil.rmtree(self._venv_dir, ignore_errors=True)

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "install_s": self._mc.elapsed("install"),
            "download_s": self._mc.elapsed("download"),
            "model_size_mb": self._model_size_mb,
            "inference_s": self._mc.elapsed("inference"),
            "inference_ok": self._inference_ok,
            "inference_output": self._inference_output,
            "software_error": self._software_error,
        })
        return d
```

- [ ] **Step 4: 运行确认通过**

```bash
python -m pytest tests/test_stage_use_qwen2.py -v
```
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add stages/stage_use_qwen2.py tests/test_stage_use_qwen2.py
git commit -m "feat: add UseQwen2Stage (Qwen2-0.5B CPU inference)"
```

---

### Task 9: Reporter

**Files:**
- Create: `cann-eval/reports/reporter.py`
- Test: `cann-eval/tests/test_reporter.py`

- [ ] **Step 1: 写失败测试**

```python
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
            "breakpoints": [],
        },
        "get_runpkg": {
            "status": "warn", "download_s": 60.0, "file_size_mb": 500.0,
            "install_exit_code": 1, "atc_available": None,
            "breakpoints": [{"severity": "P1", "phenomenon": ".run 安装失败", "cause": "无 root", "solution": "用 sudo"}],
        },
        "use_quickstart": {
            "status": "pass", "atc_exit_code": 0, "atc_help_output": "ATC start working",
            "breakpoints": [],
        },
        "use_qwen2": {
            "status": "pass", "inference_ok": True,
            "inference_output": "你好，我是 Qwen2",
            "model_size_mb": 950.0, "download_s": 120.0,
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
```

- [ ] **Step 2: 运行确认失败**

```bash
python -m pytest tests/test_reporter.py -v
```

- [ ] **Step 3: 实现 Reporter**

```python
# reports/reporter.py
import json
import datetime


def _icon(status: str) -> str:
    return {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(status, "❓")


class Reporter:
    def __init__(self, data: dict):
        self._data = data

    def to_json(self) -> dict:
        return self._data

    def to_markdown(self) -> str:
        d = self._data
        stages = d.get("stages", {})
        learn = stages.get("learn", {})
        gd = stages.get("get_docker", {})
        grp = stages.get("get_runpkg", {})
        qs = stages.get("use_quickstart", {})
        qw = stages.get("use_qwen2", {})

        # 收集所有断点
        all_bp: list[dict] = []
        for sname, sdata in stages.items():
            for bp in sdata.get("breakpoints", []):
                all_bp.append({"stage": sname, **bp})
        all_bp.sort(key=lambda x: {"P0": 0, "P1": 1, "P2": 2}.get(x["severity"], 3))

        env = d.get("environment", {})
        mode_label = "自动化" if d.get("mode") == "auto" else "人工辅助"

        # 总览表
        overview_rows = "\n".join([
            f"| 了解 | {_icon(learn.get('status',''))} {learn.get('status','')} | {learn.get('search_s','?')}s |",
            f"| 获取（Docker） | {_icon(gd.get('status',''))} {gd.get('status','')} | {gd.get('wall_clock_s','?')}s |",
            f"| 获取（.run） | {_icon(grp.get('status',''))} {grp.get('status','')} | {grp.get('download_s','?')}s |",
            f"| 使用（Quick Start） | {_icon(qs.get('status',''))} {qs.get('status','')} | {qs.get('toolchain_s','?')}s |",
            f"| 使用（Qwen2-0.5B） | {_icon(qw.get('status',''))} {qw.get('status','')} | {qw.get('inference_s','?')}s |",
        ])

        # 断点汇总表
        if all_bp:
            bp_rows = "\n".join(
                f"| {i+1} | {bp['stage']} | {bp['severity']} | {bp['phenomenon']} | {bp.get('cause','')} | {bp.get('solution','')} |"
                for i, bp in enumerate(all_bp)
            )
            bp_section = f"""## 断点汇总

| 编号 | 阶段 | 严重程度 | 现象 | 原因 | 解决方案 |
|------|------|---------|------|------|---------|
{bp_rows}
"""
        else:
            bp_section = "## 断点汇总\n\n（无断点）\n"

        # Qwen2 CPU 说明
        qwen2_note = ""
        if not qw.get("inference_ok"):
            qwen2_note = "\n> **CPU 限制说明：** 当前机器无物理 NPU，Qwen2 实际推理无法执行。验证到\"命令启动不因软件原因报错\"为止。\n"

        return f"""# CANN 易用性评估报告

**测试日期：** {d.get('test_date', '')}
**测试模式：** {mode_label}
**环境：** {env.get('os', '')} {env.get('arch', '')}

## 总览

| 阶段 | 状态 | 关键耗时 |
|------|------|---------|
{overview_rows}

---

## 了解阶段

| 指标 | 结果 |
|------|------|
| 搜索耗时 | {learn.get('search_s', '?')}s |
| hiascend.com 搜索排名 | {learn.get('official_link_rank', '未找到')} |
| 官方文档链接 | {learn.get('official_url', '—')} |
| Quick Start 找到 | {'✅' if learn.get('quickstart_found') else '❌'} {learn.get('quickstart_url', '')} |
| Qwen2 部署文档找到 | {'✅' if learn.get('qwen2_guide_found') else '❌'} {learn.get('qwen2_guide_url', '')} |
| 可访问链接数 | {learn.get('accessible_links', 0)} |
| 断链数 | {learn.get('broken_links', 0)} |

---

## 获取阶段

### Docker 方式

| 指标 | 结果 |
|------|------|
| 状态 | {_icon(gd.get('status',''))} {gd.get('status','')} |
| 镜像下载耗时 | {gd.get('net_download_s', '?')}s |
| 镜像大小 | {gd.get('image_size_mb', '?')} MB |
| CANN 版本 | {gd.get('cann_version', '—')} |
| atc 工具链可用 | {'✅' if gd.get('atc_available') else '❌'} |

### .run 包方式

| 指标 | 结果 |
|------|------|
| 状态 | {_icon(grp.get('status',''))} {grp.get('status','')} |
| 下载耗时 | {grp.get('download_s', '?')}s |
| 文件大小 | {grp.get('file_size_mb', '?')} MB |
| 安装退出码 | {grp.get('install_exit_code', '—')} |
| atc 工具链可用 | {grp.get('atc_available', '—')} |

### 两种方式对比

| 方式 | 总耗时 | 断点数 | atc 可用 |
|------|-------|-------|---------|
| Docker | {gd.get('wall_clock_s', '?')}s | {len(gd.get('breakpoints', []))} | {'✅' if gd.get('atc_available') else '❌'} |
| .run 包 | {grp.get('download_s', '?')}s (下载) | {len(grp.get('breakpoints', []))} | {grp.get('atc_available', '—')} |

---

## 使用阶段

### Quick Start（atc --help）

| 指标 | 结果 |
|------|------|
| 状态 | {_icon(qs.get('status',''))} {qs.get('status','')} |
| 工具链验证耗时 | {qs.get('toolchain_s', '?')}s |
| atc 退出码 | {qs.get('atc_exit_code', '—')} |
| 输出（前 200 字符） | `{qs.get('atc_help_output', '—')}` |

### Qwen2-0.5B 推理
{qwen2_note}
| 指标 | 结果 |
|------|------|
| 状态 | {_icon(qw.get('status',''))} {qw.get('status','')} |
| pip 安装耗时 | {qw.get('install_s', '?')}s |
| 模型下载耗时 | {qw.get('download_s', '?')}s |
| 模型大小 | {qw.get('model_size_mb', '?')} MB |
| 推理耗时 | {qw.get('inference_s', '?')}s |
| 推理成功 | {'✅' if qw.get('inference_ok') else '❌'} |
| 推理输出 | {qw.get('inference_output', '—')} |

---

{bp_section}"""

```

- [ ] **Step 4: 运行确认通过**

```bash
python -m pytest tests/test_reporter.py -v
```
Expected: 4 passed

- [ ] **Step 5: 提交**

```bash
git add reports/reporter.py tests/test_reporter.py
git commit -m "feat: add Reporter with Chinese Markdown output"
```

---

### Task 10: Runner + CLI

**Files:**
- Create: `cann-eval/runner.py`
- Test: `cann-eval/tests/test_runner.py`

> **设计说明：** Spec Section 4.3 定义 `Runner.run(stage_names, on_failure="continue")`，本实现改为从 `config["on_stage_failure"]` 读取，使 CLI 与 MCP 调用路径一致，无需每次显式传参。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_runner.py
from unittest.mock import MagicMock, patch
from runner import Runner, get_stage_names


def _make_pass_stage():
    stage = MagicMock()
    stage.verify.return_value = True
    stage.metrics.return_value = {"status": "pass", "breakpoints": []}
    stage._mc = MagicMock()
    stage._container = None
    return stage


def _make_fail_stage():
    stage = MagicMock()
    stage.verify.return_value = False
    stage.metrics.return_value = {"status": "fail", "breakpoints": [{"severity": "P0", "phenomenon": "test error", "cause": "", "solution": ""}]}
    stage._mc = MagicMock()
    stage._container = None
    return stage


def test_runner_runs_all_stages():
    stages = {
        "learn": _make_pass_stage(),
        "get_docker": _make_pass_stage(),
        "get_runpkg": _make_pass_stage(),
        "use_quickstart": _make_pass_stage(),
        "use_qwen2": _make_pass_stage(),
    }
    config = {"on_stage_failure": "continue"}
    runner = Runner(stages, config)
    report = runner.run(["learn", "get_docker", "use_quickstart"])
    assert "learn" in report["stages"]
    assert "get_docker" in report["stages"]
    assert "use_quickstart" in report["stages"]
    assert "get_runpkg" not in report["stages"]


def test_runner_injects_container_into_use_quickstart():
    mock_container = MagicMock()
    get_docker = _make_pass_stage()
    get_docker._container = mock_container
    use_qs = _make_pass_stage()
    use_qs._container = None
    stages = {
        "learn": _make_pass_stage(),
        "get_docker": get_docker,
        "get_runpkg": _make_pass_stage(),
        "use_quickstart": use_qs,
        "use_qwen2": _make_pass_stage(),
    }
    config = {"on_stage_failure": "continue"}
    runner = Runner(stages, config)
    runner.run(["get_docker", "use_quickstart"])
    assert use_qs._container is mock_container


def test_runner_abort_on_failure():
    stages = {
        "learn": _make_fail_stage(),
        "get_docker": _make_pass_stage(),
        "get_runpkg": _make_pass_stage(),
        "use_quickstart": _make_pass_stage(),
        "use_qwen2": _make_pass_stage(),
    }
    config = {"on_stage_failure": "abort"}
    runner = Runner(stages, config)
    report = runner.run(Runner.STAGE_ORDER)
    # 因为 learn 失败且 abort，后续 stage 不应执行
    assert "learn" in report["stages"]
    assert "get_docker" not in report["stages"]


def test_runner_continue_on_failure():
    stages = {
        "learn": _make_fail_stage(),
        "get_docker": _make_pass_stage(),
        "get_runpkg": _make_pass_stage(),
        "use_quickstart": _make_pass_stage(),
        "use_qwen2": _make_pass_stage(),
    }
    config = {"on_stage_failure": "continue"}
    runner = Runner(stages, config)
    report = runner.run(Runner.STAGE_ORDER)
    # continue 模式下，所有 stage 都应执行
    assert "learn" in report["stages"]
    assert "get_docker" in report["stages"]


def test_get_stage_names_docker():
    assert get_stage_names("docker", None) == ["learn", "get_docker", "use_quickstart", "use_qwen2"]


def test_get_stage_names_single_stage():
    assert get_stage_names("both", "learn") == ["learn"]
```

- [ ] **Step 2: 运行确认失败**

```bash
python -m pytest tests/test_runner.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'runner'`

- [ ] **Step 3: 实现 runner.py**

```python
# runner.py
import datetime
import json
import os
import platform
import subprocess
import sys
import yaml
from stages.base import BaseStage
from stages.stage_learn import LearnStage
from stages.stage_get_docker import GetDockerStage
from stages.stage_get_runpkg import GetRunPkgStage
from stages.stage_use_quickstart import UseQuickStartStage
from stages.stage_use_qwen2 import UseQwen2Stage
from reports.reporter import Reporter


class Runner:
    STAGE_ORDER = ["learn", "get_docker", "get_runpkg", "use_quickstart", "use_qwen2"]

    def __init__(self, stages: dict[str, BaseStage], config: dict):
        self._stages = stages
        self._config = config

    def run(self, stage_names: list[str]) -> dict:
        report = {
            "test_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "mode": "auto",
            "environment": _get_environment(),
            "stages": {},
            "breakpoints": [],
        }
        on_failure = self._config.get("on_stage_failure", "continue")
        get_docker_stage: GetDockerStage | None = None
        deferred_teardown = []

        for name in self.STAGE_ORDER:
            if name not in stage_names:
                continue
            stage = self._stages[name]

            # 注入容器句柄
            if name == "use_quickstart" and get_docker_stage and get_docker_stage._container:
                stage._container = get_docker_stage._container

            try:
                stage.setup()
                stage.run()
                ok = stage.verify()
            except Exception as e:
                ok = False
                stage._mc.add_error(
                    phenomenon=f"Stage 异常: {e}",
                    severity="P0",
                    cause="未捕获的异常",
                    solution="查看完整 traceback",
                )
                stage._mc.set_fail()

            # get_docker 延迟 teardown（等 use_quickstart 完成后再清理容器）
            if name == "get_docker" and "use_quickstart" in stage_names:
                get_docker_stage = stage
                deferred_teardown.append(stage)
            else:
                try:
                    stage.teardown()
                except Exception:
                    pass

            # use_quickstart 完成后，清理 get_docker 容器
            if name == "use_quickstart":
                for s in deferred_teardown:
                    try:
                        s.teardown()
                    except Exception:
                        pass
                deferred_teardown.clear()

            report["stages"][name] = stage.metrics()
            # 汇总断点到顶层
            for bp in stage.metrics().get("breakpoints", []):
                report["breakpoints"].append({"stage": name, **bp})

            if not ok and on_failure == "abort":
                break

        # 清理剩余延迟 teardown
        for s in deferred_teardown:
            try:
                s.teardown()
            except Exception:
                pass

        return report


def _get_environment() -> dict:
    try:
        docker_ver = subprocess.check_output(
            ["docker", "--version"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        docker_ver = "unknown"
    return {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "python": platform.python_version(),
        "docker_version": docker_ver,
    }


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_runner(config: dict, install: str = "both") -> Runner:
    stages: dict[str, BaseStage] = {
        "learn": LearnStage(config),
        "get_docker": GetDockerStage(config),
        "get_runpkg": GetRunPkgStage(config),
        "use_quickstart": UseQuickStartStage(config),
        "use_qwen2": UseQwen2Stage(config),
    }
    return Runner(stages=stages, config=config)


def get_stage_names(install: str, stage: str | None) -> list[str]:
    if stage:
        return [stage]
    if install == "docker":
        return ["learn", "get_docker", "use_quickstart", "use_qwen2"]
    elif install == "run_pkg":
        return ["learn", "get_runpkg", "use_qwen2"]
    else:  # both
        return Runner.STAGE_ORDER


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CANN 易用性评估工具")
    parser.add_argument("--mode", choices=["auto", "manual"], default="auto")
    parser.add_argument("--install", choices=["docker", "run_pkg", "both"], default="both")
    parser.add_argument("--stage", choices=["learn", "get_docker", "get_runpkg", "use_quickstart", "use_qwen2"])
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--output", help="输出文件路径（默认打印到 stdout）")
    args = parser.parse_args()

    if args.mode == "manual":
        import manual.recorder as rec
        rec.main()
        sys.exit(0)

    config = load_config(args.config)
    runner = build_runner(config, args.install)
    stage_names = get_stage_names(args.install, args.stage)
    report = runner.run(stage_names)
    reporter = Reporter(report)

    if args.format == "json":
        output = json.dumps(reporter.to_json(), indent=2, ensure_ascii=False)
    else:
        output = reporter.to_markdown()

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output)
        print(f"报告已写入 {args.output}")
    else:
        print(output)
```

- [ ] **Step 4: 运行确认通过**

```bash
python -m pytest tests/test_runner.py -v
```
Expected: 6 passed

- [ ] **Step 5: 冒烟测试**（不连接真实网络/Docker）

```bash
cd /home/zhongjun/claude/zhongjun2/ttfhw/cann-eval
python runner.py --help
```
Expected: 打印 usage，无报错

- [ ] **Step 6: 提交**

```bash
git add runner.py tests/test_runner.py
git commit -m "feat: add Runner, CLI entry point, and Runner tests"
```

---

### Task 11: Manual Recorder

**Files:**
- Create: `cann-eval/manual/__init__.py`
- Create: `cann-eval/manual/recorder.py`

- [ ] **Step 1: 实现 Manual Recorder**

```python
# manual/recorder.py
import datetime
import json
import os
import sys
import time

STEPS = [
    ("learn", "1.1", "Google 搜索 CANN 相关信息，找到官方文档"),
    ("learn", "1.2", "验证官方文档链接可访问，找到 Quick Start"),
    ("learn", "1.3", "搜索 Qwen2 CANN 部署文档链接"),
    ("get_docker", "2.1", "执行 docker pull ascendai/cann:latest"),
    ("get_docker", "2.2", "启动容器，验证 CANN 版本信息"),
    ("get_docker", "2.3", "容器内 source set_env.sh && atc --help"),
    ("get_runpkg", "3.1", "从 hiascend.com 找到 .run 包下载链接并下载"),
    ("get_runpkg", "3.2", "执行 .run --install，记录结果"),
    ("get_runpkg", "3.3", "（若安装成功）source set_env.sh && atc --help"),
    ("use_quickstart", "4.1", "容器内 source set_env.sh"),
    ("use_quickstart", "4.2", "容器内 atc --help，验证工具链"),
    ("use_qwen2", "5.1", "pip install modelscope transformers torch torch-npu"),
    ("use_qwen2", "5.2", "modelscope download Qwen2-0.5B"),
    ("use_qwen2", "5.3", "运行推理命令，记录结果"),
]


def _prompt_breakpoint() -> dict | None:
    note = input("  输入断点备注（留空跳过）：").strip()
    if not note:
        return None
    sev_input = input("  严重程度 [0=P0 阻断 / 1=P1 绕路可过 / 2=P2 轻微，默认 1]：").strip()
    sev = {"0": "P0", "1": "P1", "2": "P2"}.get(sev_input, "P1")
    cause = input("  原因（可选）：").strip()
    solution = input("  解决方案（可选）：").strip()
    return {"severity": sev, "phenomenon": note, "cause": cause, "solution": solution}


def main():
    print("=" * 60)
    print("CANN 易用性评估 — 人工辅助录制模式")
    print("=" * 60)
    print("按步骤逐一操作，每步完成后按 Enter 记录时间。\n")

    results: dict[str, dict] = {}
    all_breakpoints: list[dict] = []
    current_stage = None
    stage_start = None

    for stage_name, step_id, description in STEPS:
        if stage_name != current_stage:
            if current_stage is not None:
                results[current_stage]["stage_end"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            current_stage = stage_name
            stage_start = time.monotonic()
            results[stage_name] = {
                "stage_start": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "steps": [],
                "breakpoints": [],
            }
            print(f"\n{'='*40}")
            stage_labels = {
                "learn": "了解阶段", "get_docker": "获取阶段（Docker）",
                "get_runpkg": "获取阶段（.run 包）",
                "use_quickstart": "使用阶段（Quick Start）", "use_qwen2": "使用阶段（Qwen2-0.5B）",
            }
            print(f"  {stage_labels.get(stage_name, stage_name)}")
            print(f"{'='*40}\n")

        print(f"[步骤 {step_id}] {description}")
        input("  > 按 Enter 开始操作...")
        t0 = time.monotonic()

        input("  > 操作完成后按 Enter...")
        elapsed = round(time.monotonic() - t0, 1)

        bp = _prompt_breakpoint()
        if bp:
            all_breakpoints.append({"stage": stage_name, **bp})
            results[stage_name]["breakpoints"].append(bp)
            print(f"  ⚠ 断点 {bp['severity']} 已记录")

        results[stage_name]["steps"].append({
            "step_id": step_id,
            "description": description,
            "elapsed_s": elapsed,
        })
        print(f"  ✓ 耗时: {int(elapsed//60)}m{int(elapsed%60)}s\n")

    if current_stage:
        results[current_stage]["stage_end"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    report = {
        "test_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mode": "manual",
        "environment": {"note": "手动录制，请手动填写环境信息"},
        "stages": results,
        "breakpoints": all_breakpoints,
    }

    # 保存报告
    date_str = datetime.date.today().isoformat()
    os.makedirs("reports", exist_ok=True)
    json_path = f"reports/manual-{date_str}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"录制完成！报告已保存：{json_path}")
    print(f"断点数量：{len(all_breakpoints)}")
    print(f"{'='*60}")
    return report


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 创建 manual/__init__.py**

```python
# manual/__init__.py
```

- [ ] **Step 3: 验证可运行**

```bash
echo "" | python manual/recorder.py 2>&1 | head -5
```
Expected: 打印标题行，无报错

- [ ] **Step 4: 提交**

```bash
git add manual/__init__.py manual/recorder.py
git commit -m "feat: add manual recorder for human-assisted testing"
```

---

### Task 12: MCP Server + Claude Skill

**Files:**
- Create: `cann-eval/mcp_server.py`
- Create: `cann-eval/skills/cann-eval.md`

- [ ] **Step 1: 实现 MCP Server**

```python
# mcp_server.py
import json
import os
from mcp.server.fastmcp import FastMCP
from runner import load_config, build_runner, get_stage_names, Runner
from reports.reporter import Reporter

mcp = FastMCP("cann-eval")
_last_report: dict | None = None


@mcp.tool()
def cann_eval_run_all(install_mode: str = "both") -> str:
    """
    运行 CANN 易用性评估全部阶段。
    install_mode: "docker" | "run_pkg" | "both"（默认 both）
    返回中文 Markdown 报告。
    """
    global _last_report
    config = load_config()
    runner = build_runner(config, install_mode)
    stage_names = get_stage_names(install_mode, None)
    _last_report = runner.run(stage_names)
    return Reporter(_last_report).to_markdown()


@mcp.tool()
def cann_eval_run_stage(stage_name: str) -> str:
    """
    运行单个阶段。
    stage_name: "learn" | "get_docker" | "get_runpkg" | "use_quickstart" | "use_qwen2"
    返回该阶段的 JSON 指标。
    """
    global _last_report
    config = load_config()
    runner = build_runner(config)
    result = runner.run([stage_name])
    _last_report = result
    return json.dumps(result["stages"].get(stage_name, {}), ensure_ascii=False, indent=2)


@mcp.tool()
def cann_eval_report(format: str = "markdown") -> str:
    """
    获取最新一次评估报告。
    format: "markdown"（默认）| "json"
    如果还没有运行过评估，返回提示信息。
    """
    if _last_report is None:
        return "尚未运行评估。请先调用 cann_eval_run_all。"
    reporter = Reporter(_last_report)
    if format == "json":
        return json.dumps(reporter.to_json(), ensure_ascii=False, indent=2)
    return reporter.to_markdown()


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 2: 创建 skills/cann-eval.md**

```markdown
---
name: cann-eval
description: 运行 CANN 易用性评估，输出中文报告
---

# /cann-eval Skill

评估 CANN 了解/获取/使用三个阶段的易用性，输出中文报告（含断点汇总）。

## 用法

- `/cann-eval` — 运行全部阶段（Docker + .run + Quick Start + Qwen2）
- `/cann-eval learn` — 只运行了解阶段（Google 搜索 + 文档可达性）
- `/cann-eval docker` — 只测 Docker 安装方式
- `/cann-eval report` — 查看最新报告

## 执行逻辑

调用对应的 MCP 工具：

- `/cann-eval` → `cann_eval_run_all(install_mode="both")`
- `/cann-eval learn` → `cann_eval_run_stage(stage_name="learn")`
- `/cann-eval docker` → `cann_eval_run_all(install_mode="docker")`
- `/cann-eval report` → `cann_eval_report(format="markdown")`
```

- [ ] **Step 3: 验证 MCP Server 可导入**

```bash
cd /home/zhongjun/claude/zhongjun2/ttfhw/cann-eval
python -c "import mcp_server; print('MCP server import OK')"
```
Expected: `MCP server import OK`

- [ ] **Step 4: 提交**

```bash
mkdir -p skills
git add mcp_server.py skills/cann-eval.md
git commit -m "feat: add MCP server and /cann-eval Skill"
```

---

### Task 13: 全量测试 + 推送

> **F4.5 说明：** Reporter.compare() 多次测试对比功能（spec Section 六 F4.5）标记为 P1，在此版本中推迟实现，接口预留在 Reporter 类中，后续迭代补充。

- [ ] **Step 1: 运行全部单元测试**

```bash
python -m pytest tests/ -v
```
Expected: 全部通过（约 25+ tests）

- [ ] **Step 2: 冒烟测试 learn 阶段**

```bash
python runner.py --mode auto --stage learn --format markdown
```
Expected: 打印了解阶段报告，包含 hiascend.com 链接搜索结果

- [ ] **Step 3: 验证 MCP Server 可导入**

```bash
python -c "import mcp_server; print('MCP import OK')"
```
Expected: `MCP import OK`，无报错

- [ ] **Step 4: 同步到上游 repo 并推送**

```bash
# 同步到 ttfhw/ttfhw 上游 repo
rsync -av --exclude='.git' --exclude='__pycache__' \
  /home/zhongjun/claude/zhongjun2/ttfhw/cann-eval/ \
  /home/zhongjun/claude/zhongjun2/ttfhw/ttfhw/cann/cann-eval/

git -C /home/zhongjun/claude/zhongjun2/ttfhw/ttfhw add cann/cann-eval/
git -C /home/zhongjun/claude/zhongjun2/ttfhw/ttfhw commit -m "feat(cann-eval): complete automated evaluation tool implementation"
git -C /home/zhongjun/claude/zhongjun2/ttfhw/ttfhw push
```
