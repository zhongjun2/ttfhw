# CANN 易用性评估工具 — 架构设计规格

**版本：** v1.1
**创建日期：** 2026-03-26
**对应需求：** `docs/requirements.md` v1.0
**状态：** 正式

---

## 一、目标

构建一套自动化 + 人工辅助的评估工具，量化新用户从零开始使用 CANN 完成模型推理的全流程体验，输出中文结构化报告。

覆盖需求文档中的三个阶段：了解（F1）、获取（F2）、使用（F3），并实现报告输出（F4）和三种接口（F5）。

---

## 二、整体架构

采用平铺 Stage 模式，5 个 Stage 实现 3 个逻辑阶段，Runner 统一编排，Reporter 汇总输出。

```
逻辑阶段     Stage 实现
────────     ──────────
了解          LearnStage
获取          GetDockerStage    （Docker 方式，完成后保留容器）
              GetRunPkgStage    （.run 包方式，独立运行）
使用          UseQuickStartStage（依赖 GetDockerStage 容器）
              UseQwen2Stage     （宿主机，独立 venv）
```

Runner 容器传递：`GetDockerStage._container` → Runner 注入 → `UseQuickStartStage._container`

两种安装方式（GetDocker / GetRunPkg）默认都运行，报告中输出对比（对应 F2.6）。

---

## 三、文件结构

```
cann-eval/
├── config.yaml                       # 配置（镜像、超时、.run URL 等）
├── runner.py                         # CLI 入口 + Runner 类
├── requirements.txt                  # Python 依赖
├── mcp_server.py                     # MCP Server（3 个工具，F5.1）
├── skills/
│   └── cann-eval.md                  # Claude Skill 定义（/cann-eval，F5.2）
├── stages/
│   ├── __init__.py
│   ├── base.py                       # BaseStage 抽象接口
│   ├── stage_learn.py                # 了解阶段（F1）
│   ├── stage_get_docker.py           # 获取阶段：Docker 方式（F2.1 F2.4）
│   ├── stage_get_runpkg.py           # 获取阶段：.run 包方式（F2.2 F2.3 F2.4）
│   ├── stage_use_quickstart.py       # 使用阶段：Quick Start（F3.1）
│   └── stage_use_qwen2.py            # 使用阶段：Qwen2-0.5B（F3.2 F3.3 F3.4）
├── metrics/
│   ├── __init__.py
│   └── collector.py                  # MetricsCollector：计时 + 断点收集（F4.4）
├── reports/
│   ├── __init__.py
│   └── reporter.py                   # Reporter：JSON + 中文 Markdown（F4.1 F4.2 F4.3）
├── manual/
│   └── recorder.py                   # 人工辅助 CLI 录制器
└── tests/
    ├── __init__.py
    ├── test_stage_learn.py
    ├── test_stage_get_docker.py
    ├── test_stage_get_runpkg.py
    ├── test_stage_use_quickstart.py
    └── test_stage_use_qwen2.py
```

---

## 四、接口定义

### 4.1 BaseStage

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

### 4.2 MetricsCollector

```python
class MetricsCollector:
    def start(self, name: str) -> None
    def stop(self, name: str) -> None
    def elapsed(self, name: str) -> float | None   # 秒，保留 3 位小数
    def add_error(self, msg: str, severity: str = "P1") -> None  # 添加断点
    def set_warn(self) -> None
    def set_fail(self) -> None
    def status(self) -> str            # "pass" | "warn" | "fail"
    def to_dict(self) -> dict
```

断点（breakpoint）存储结构：
```python
{"severity": "P0"|"P1"|"P2", "message": str}
```
- P0：阻断性，后续步骤无法进行
- P1：绕路可过（默认）
- P2：轻微问题

### 4.3 Runner

```python
class Runner:
    def run(self, stage_names: list[str], on_failure: str = "continue") -> dict
```

编排逻辑：
1. 按顺序执行各 Stage 的 setup → run → verify
2. 在 `use_quickstart` 前将 `get_docker._container` 注入
3. `get_docker` 的 teardown 推迟到 `use_quickstart` teardown 之后执行
4. 任一 Stage 失败时按 `on_failure` 决定继续或终止

### 4.4 Reporter

```python
class Reporter:
    def to_json(self) -> dict
    def to_markdown(self) -> str    # 中文 Markdown，含断点汇总表
```

---

## 五、各 Stage 详细规格

### 5.1 LearnStage（F1）

**依赖：** `duckduckgo-search`、`requests`

**流程：**
1. 搜索 `"CANN 昇腾 安装"`（`DDGS().text(query, max_results=10)`），记录耗时（F1.4）
2. 在结果 URL 中找 `hiascend.com` 链接，记录排名（F1.1 F1.4）
3. HTTP HEAD 验证该链接可访问（F1.2）
4. 搜索 `"Qwen2 CANN 昇腾 部署"`，找部署文档链接（F1.3）
5. HTTP HEAD 检查所有找到链接，统计断链（F1.5）

**Metrics：**
```
search_s              搜索耗时（秒）
official_link_rank    hiascend.com 在搜索结果中的排名（null 表示未找到）
official_url          找到的 hiascend.com URL
official_accessible   bool
quickstart_url        Quick Start 文档 URL（来自搜索结果或官方链接导航）
quickstart_found      bool
qwen2_guide_url       Qwen2 部署文档 URL
qwen2_guide_found     bool
accessible_links      可访问链接总数
broken_links          断链总数
status / errors（含断点列表）
```

### 5.2 GetDockerStage（F2.1 F2.4）

**依赖：** `docker` Python SDK

**流程：**
1. `docker.from_env()` 初始化
2. `images.pull("ascendai/cann:latest")`，记录下载耗时 + 镜像大小（F2.1）
3. `containers.run(image, detach=True, tty=True)` 启动容器
4. 容器内执行 `source /usr/local/Ascend/cann-*/set_env.sh && atc --help`，验证工具链（F2.4）
5. 读取容器内 CANN 版本信息
6. 保留 `self._container` 供 Runner 传给 UseQuickStartStage

**Metrics：**
```
net_download_s        镜像下载耗时
image_size_mb         镜像大小（MB）
wall_clock_s          阶段总耗时
cann_version          CANN 版本号（从容器内读取）
atc_available         bool（atc --help 退出码 == 0）
status / errors
```

### 5.3 GetRunPkgStage（F2.2 F2.3 F2.4）

**依赖：** `requests`

**约束：** hiascend.com 为 SPA（Nuxt.js），无法自动抓取下载链接。.run 包 URL 在 `config.yaml` 中手动配置，需随版本更新。

**流程：**
1. 从 `config.yaml` 读取 `run_pkg_url`，HTTP GET 下载文件，记录大小 + 耗时（F2.2）
2. `chmod +x`，执行 `./Ascend-cann-toolkit_*.run --install`（F2.3）
   - 无 root 时预期失败（exit code ≠ 0），记为断点 P1
3. 若安装成功（root 环境），执行 `source set_env.sh && atc --help` 验证工具链（F2.4）
4. 捕获所有错误信息（F2.5）
5. teardown 时删除下载的 .run 临时文件

**Metrics：**
```
download_s            下载耗时
file_size_mb          .run 文件大小
install_exit_code     安装命令退出码
install_stderr        安装错误输出（前 500 字符）
atc_available         bool（安装成功后验证；无 root 时为 null）
status / errors
```

### 5.4 UseQuickStartStage（F3.1）

**依赖：** GetDockerStage 容器句柄（由 Runner 注入 `self._container`）

**流程：**
1. 容器内执行：
   ```bash
   source /usr/local/Ascend/cann-*/set_env.sh && which atc && atc --help
   ```
2. 检查退出码，捕获 stdout 前 200 字符
3. teardown 时停止并删除容器（释放 GetDockerStage 保留的容器）

**Metrics：**
```
toolchain_s           工具链验证耗时
set_env_found         bool
atc_exit_code         int
atc_help_output       str（前 200 字符）
status / errors
```

### 5.5 UseQwen2Stage（F3.2 F3.3 F3.4）

**依赖：** `modelscope`、`transformers`、`torch`（宿主机安装，独立 venv）

**模型：** `qwen/Qwen2-0.5B`（约 1 GB，CPU 可运行）

**注意：** F3.2 要求配置 torch_npu + CANN 环境；在纯 CPU 机器上，torch_npu 可安装但无法初始化 NPU 设备（预期行为）。验证目标是软件层正常，不要求 NPU 推理成功。

**流程：**
1. 创建隔离 venv，安装：`modelscope transformers torch torch-npu`，记录安装耗时（F3.2）
2. `modelscope download --model qwen/Qwen2-0.5B --local_dir <cache_dir>`，记录下载大小 + 耗时（F3.3）
3. 运行推理命令（F3.4）：
   ```python
   from transformers import AutoModelForCausalLM, AutoTokenizer
   model = AutoModelForCausalLM.from_pretrained(path, device_map="cpu")
   tok = AutoTokenizer.from_pretrained(path)
   out = model.generate(**tok("你好", return_tensors="pt"), max_new_tokens=5)
   print(tok.decode(out[0], skip_special_tokens=True))
   ```
4. 分析退出码：exit_code == 0 → pass；若失败，判断是否为软件原因（非 NPU 驱动缺失）
5. teardown 时删除 venv（保留模型缓存可复用）

**Metrics：**
```
install_s             pip 安装耗时
download_s            模型下载耗时
model_size_mb         模型文件总大小
inference_s           推理耗时
inference_ok          bool
inference_output      str（推理输出，若成功）
software_error        bool（失败且不是 NPU 缺失原因）
status / errors
```

---

## 六、报告格式（F4）

### JSON 输出结构（F4.1）

```json
{
  "test_date": "2026-03-26T07:00:00Z",
  "mode": "auto",
  "environment": {"os": "Ubuntu 24.04", "arch": "x86_64", "docker_version": "29.x"},
  "stages": {
    "learn": { "status": "warn", "search_s": 2.1, "official_link_rank": 1, ... },
    "get_docker": { "status": "pass", "net_download_s": 360, "image_size_mb": 4080, ... },
    "get_runpkg": { "status": "warn", "install_exit_code": 1, ... },
    "use_quickstart": { "status": "pass", "atc_available": true, ... },
    "use_qwen2": { "status": "pass", "inference_ok": true, ... }
  },
  "breakpoints": [
    {
      "stage": "get_runpkg",
      "severity": "P1",
      "phenomenon": ".run 安装返回非零退出码",
      "cause": "无 root 权限",
      "solution": "使用 Docker 方式替代，或以 root 执行"
    }
  ]
}
```

### Markdown 报告结构（F4.2 F4.3）

```markdown
# CANN 易用性评估报告

## 总览
测试日期 / 环境 / 模式 / 各阶段状态汇总表

## 了解阶段
操作步骤 | 找到的链接（含可访问性）| 断点

## 获取阶段
### Docker 方式
步骤 + 耗时 + 断点

### .run 包方式
步骤 + 耗时 + 断点

### 两种方式对比
| 方式 | 总耗时 | 断点数 | atc 可用 |

## 使用阶段
### Quick Start（atc --help）
步骤 + 耗时 + 断点

### Qwen2-0.5B 推理
步骤 + 耗时 + 断点（含 CPU 限制说明）

## 断点汇总
| 编号 | 阶段 | 严重程度 | 现象 | 原因 | 解决方案 |
（按 P0 → P1 → P2 排序）
```

### 多次测试对比（F4.5，P1）

报告文件以日期命名（`reports/YYYY-MM-DD.json`），Reporter 提供 `compare(report_a, report_b)` 方法生成差异对比表，实现在后续迭代中添加。

---

## 七、人工辅助录制器（manual/recorder.py）

按预设步骤列表逐步提示，步骤与自动化 Stage 一一对应（5 组共 15 步）。每步按 Enter 开始/结束计时，支持输入断点备注（现象 + 严重程度），最终生成与自动化相同格式的 JSON + Markdown 报告。

```
[步骤 2.1] 执行官方镜像拉取命令
> 按 Enter 开始...（计时中）
> 按 Enter 结束，或输入断点备注（留空跳过）：ascendhub DNS 解析失败
  选择严重程度 [0=P0/1=P1/2=P2，默认 1]：
  ✓ 耗时: 0m23s  ⚠ 断点 P1 已记录
```

---

## 八、MCP Server（mcp_server.py，F5.1）

3 个工具：
- `cann_eval_run_all(install_mode: "docker"|"run_pkg"|"both" = "both")` — 运行全部 Stage
- `cann_eval_run_stage(stage_name: str)` — 运行单个 Stage
- `cann_eval_report(format: "markdown"|"json" = "markdown")` — 读取最新报告

---

## 九、Claude Skill（skills/cann-eval.md，F5.2）

`/cann-eval` 命令触发 MCP 工具，支持参数：
- `/cann-eval` — 运行全部阶段
- `/cann-eval learn` — 只运行了解阶段
- `/cann-eval report` — 查看最新报告

---

## 十、CLI 入口（runner.py，F5.3）

```bash
python runner.py                          # 运行全部阶段
python runner.py --install docker         # 只测 Docker 安装
python runner.py --install run_pkg        # 只测 .run 安装
python runner.py --stage learn            # 只运行了解阶段
python runner.py --format markdown        # 输出 Markdown 报告
python manual/recorder.py                 # 人工辅助模式
```

---

## 十一、config.yaml 关键字段

```yaml
cann_image: "ascendai/cann:latest"
run_pkg_url: ""                        # .run 下载 URL，需手动更新（hiascend.com SPA 无法自动抓取）
qwen2_model: "qwen/Qwen2-0.5B"
qwen2_cache_dir: "/tmp/qwen2_cache"

timeout:
  learn_s: 60
  get_docker_s: 600
  get_runpkg_s: 300
  use_quickstart_s: 60
  use_qwen2_s: 600

on_stage_failure: continue             # continue | abort
```

---

## 十二、已知约束

| 约束 | 影响阶段 | 说明 |
|------|---------|------|
| hiascend.com 为 SPA | 获取（.run） | .run 下载 URL 需手动配置，无法自动抓取 |
| 无物理 NPU | 使用（Qwen2） | CPU 上运行 Qwen2-0.5B；torch_npu 安装但无法初始化 NPU |
| .run 安装需 root | 获取（.run） | 无 root 时预期失败，记为断点 P1 |
| ascendhub.huawei.com DNS | 获取（Docker） | 官方文档地址公网不可解析；使用 ascendai/cann:latest 替代 |
| DuckDuckGo 频率限制 | 了解 | 频繁搜索可能触发限流；添加请求间隔 |
