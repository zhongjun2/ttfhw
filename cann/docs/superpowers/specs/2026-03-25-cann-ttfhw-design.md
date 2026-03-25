# CANN TTFHW 自动化测试框架 — 设计规格

**日期：** 2026-03-25
**版本：** 1.1
**场景：** Ascend CANN 社区，端到端全链路（了解→获取→使用→贡献）

---

## 1. 目标

构建一套可重复执行、自动化、多维指标的测试框架，衡量开发者在 Ascend CANN 社区经历四个阶段的时间成本与体验质量，供后续与其他 AI 框架社区（CUDA、ROCm 等）横向对比。

**非目标：** 引导式交互、真实用户招募测试。注：使用阶段通过 CANN 内置 CPU 仿真模式运行，不依赖物理 NPU 硬件（见第5节）。

---

## 2. 核心场景

> 模拟全新开发者：搜索发现 CANN → 拉取环境 → 编写运行自定义算子 → 向社区提交贡献并追踪 CI

- **场景标识：** `zero-to-custom-op`
- **社区标识：** `cann`
- 单一场景覆盖全部四个阶段，保证测试结果的整体代表性。

---

## 3. 运行环境

- **容器：** 官方 CANN Docker 镜像（版本通过 `config.yaml` 锁定）
- **算子执行：** 使用 CANN 内置 CPU 仿真模式（AiCPU 路径），无需物理 NPU
- **执行方式：** 全自动，无需人工干预
- **可重复性：** Docker 标准化环境，屏蔽机器差异

---

## 4. 架构

### 4.1 目录结构

```
ttfhw-cann/
├── runner.py                   # 主入口，串联各阶段
├── stages/
│   ├── base.py                 # Stage 基类（统一接口）
│   ├── stage_learn.py          # 阶段1：了解
│   ├── stage_get.py            # 阶段2：获取
│   ├── stage_use.py            # 阶段3：使用
│   └── stage_contribute.py     # 阶段4：贡献（含CI追踪）
├── metrics/
│   └── collector.py            # 统一指标收集器
├── reports/
│   └── reporter.py             # JSON + Markdown 报告输出
├── fixtures/
│   └── custom_op/              # 标准测试算子（AiCPU AddCustom，版本与镜像锁定）
├── mcp_server.py               # MCP 服务入口
├── skills/                     # Claude Skill 定义文件
└── config.yaml                 # 配置（镜像版本、超时、token等，见第9节）
```

### 4.2 Stage 统一接口

```python
class BaseStage:
    def setup(self) -> None      # 准备环境
    def run(self) -> None        # 执行操作（记录步骤数、错误）
    def verify(self) -> bool     # 验证成功，返回 True/False
    def teardown(self) -> None   # 清理环境
    def metrics(self) -> dict    # 返回收集的指标（含 errors 数组）
```

Runner 依次调用每个 Stage，收集指标。某阶段 `verify()` 返回 False 时，默认行为为记录失败并**继续**执行后续阶段（可在 `config.yaml` 中配置为 `abort`）。

### 4.3 阶段状态定义

每个阶段的状态为 `pass` / `warn` / `fail`，通用定义如下：

| 状态 | 含义 |
|------|------|
| `pass` | 成功标准全部满足，无错误 |
| `warn` | 核心成功标准满足，但存在非致命异常（如有断链但主文档可达、有编译警告但运行成功） |
| `fail` | 核心成功标准未满足，或超时，或出现无法继续的错误 |

各阶段具体的 `warn` 触发条件见第5节各阶段定义。

---

## 5. 四个阶段定义

### 阶段1：了解（Learn）

**起点：** 搜索工具关键词搜索（非直接访问已知URL）

**自动化流程：**
1. 调用搜索 API 搜索关键词：`"Ascend CANN 快速入门"`
2. 从搜索结果中识别官方链接（判定规则：URL 包含 `gitcode.com/ascend` 或 `hiascend.com`）
3. 访问识别到的主页，导航到快速入门文档（最多跳转 5 次）
4. 验证关键资源链接可达性（安装指南、API文档、示例代码）

**边界情况：**
- 搜索返回零结果 → 状态 `fail`，记录 `errors: ["search_no_results"]`
- 搜索有结果但无匹配官方链接 → 状态 `fail`，记录 `errors: ["no_official_link_found"]`
- 5 次跳转内未找到快速入门 → 状态 `fail`，记录 `errors: ["quickstart_not_reachable"]`
- `broken_links > 0` 但快速入门页可达 → 状态 `warn`

**`broken_links` 范围：** 快速入门文档页面内的所有外链（不递归爬取）

**成功标准（pass）：** 官方链接在搜索结果中找到；快速入门页可达；`broken_links == 0`

**关键指标：**

| 字段 | 说明 |
|------|------|
| `search_s` | 搜索 API 调用耗时 |
| `official_link_rank` | 官方链接在搜索结果中的位置（从1计） |
| `nav_hops` | 从搜索结果到快速入门页的跳转次数 |
| `accessible_links` | 快速入门页内可访问链接数 |
| `broken_links` | 快速入门页内断链数 |
| `errors` | 错误信息数组 |

---

### 阶段2：获取（Get）

**自动化流程：**
1. `docker pull <cann_image>:<version>`
2. `docker run` 启动容器
3. 验证环境变量（`ASCEND_TOOLKIT_HOME` 等）
4. 运行 `cann-info` 或等效命令确认版本输出

**"setup_steps" 计数规则：** 每条独立的 shell 命令（含 export、source）计为 1 步。

**边界情况：**
- Docker pull 超时（超过 `config.timeout.get_s`）→ `fail`，`errors: ["docker_pull_timeout"]`
- Docker pull 失败（镜像不存在、认证失败等）→ `fail`，记录具体错误
- 容器启动失败 → `fail`，`errors: ["container_start_failed"]`
- `cann-info` 命令不存在 → `fail`，`errors: ["cann_info_not_found"]`
- 部分步骤失败时，`net_download_s` 记录实际完成的下载时间，未完成字段记 `null`

**成功标准（pass）：** 镜像拉取成功；容器启动；`cann-info` 输出版本号

**关键指标：**

| 字段 | 说明 |
|------|------|
| `wall_clock_s` | 全流程挂钟时间（含下载） |
| `net_download_s` | 实际下载时间（去除命令执行开销） |
| `image_size_mb` | 镜像大小 |
| `setup_steps` | 环境验证步骤数 |
| `errors` | 错误信息数组 |

---

### 阶段3：使用（Use）

**算子选择：** AiCPU AddCustom 算子（运行在 CPU，无需物理 NPU）。fixtures 版本与 `config.yaml` 中的镜像版本锁定，镜像升级时同步更新 fixtures。

**自动化流程：**
1. 将 `fixtures/custom_op/` 复制到容器内
2. 编译算子（`bash build.sh`）
3. 运行推理（`python run.py`）
4. 验证输出与参考值误差 < `1e-5`

**边界情况：**
- 编译报 warning 但通过 → `warn`
- 编译报错 → `fail`
- 运行报错或输出误差 ≥ `1e-5` → `fail`

**成功标准（pass）：** 编译通过无 error；运行输出误差 < `1e-5`

**关键指标：**

| 字段 | 说明 |
|------|------|
| `compile_s` | 编译耗时 |
| `run_s` | 推理运行耗时 |
| `compile_errors` | 编译 error 数量 |
| `compile_warnings` | 编译 warning 数量 |
| `run_errors` | 运行错误数量 |
| `errors` | 错误信息数组 |

---

### 阶段4：贡献（Contribute）

#### 认证与账号模型

- 需在 `config.yaml` 中配置 `gitcode_token`，权限要求：`issues:write`（4a）、`pull_requests:write`（4b）
- PR 提交目标：从**测试专用 fork**（`ttfhw-bot/cann`）向上游仓库（`ascend/cann`）提交 PR，避免污染上游 Issue 列表（PR 可提交到上游，但建议在 PR 描述中注明是自动化测试）
- 幂等性：每次运行在 PR 标题中包含时间戳，避免重复冲突；Issue 同理

#### 4a. 基础贡献：提交 Issue

**自动化流程：**
1. 通过 Gitcode API 提交标准化测试 Issue（标题含时间戳）
2. 记录 Issue 编号和提交时间
3. 轮询检测首次响应（间隔 30s，超时由 `config.timeout.issue_response_s` 控制，默认 3600s）

**`first_response_s` 计时边界：**
- **开始：** Gitcode API 返回 Issue 创建成功的时间戳
- **结束：** Issue 上第一条评论（机器人或人工均计）出现的时间戳
- **超时：** 超过 `config.timeout.issue_response_s` 则记录 `null`，状态为 `warn`

**成功标准（pass）：** Issue 创建成功，返回 Issue 编号

**关键指标：**

| 字段 | 说明 |
|------|------|
| `submit_s` | Issue 提交 API 调用耗时 |
| `first_response_s` | 首次响应时间（null 表示超时） |
| `errors` | 错误信息数组 |

#### 4b. 高级贡献：提交 PR 并追踪 CI

**自动化流程：**
1. 将 fixtures 算子代码推送到 fork 仓库的新分支
2. 通过 Gitcode API 向上游提交 PR
3. 监听 PR 的 CI 流水线状态（轮询间隔 60s）
4. 分阶段记录 CI 各环节时间

**CI 子时间边界定义：**

| 字段 | 开始事件 | 结束事件 |
|------|---------|---------|
| `ci_queue_s` | PR 创建完成（API 返回） | CI 流水线第一个 Job 状态变为 `running` |
| `ci_prepare_s` | CI Job 状态变为 `running` | CI Job 内第一个测试步骤开始（日志中出现首行测试输出） |
| `ci_run_s` | CI Job 内第一个测试步骤开始 | CI Job 状态变为 `success` 或 `failed` |
| `ci_total_s` | PR 创建完成（API 返回） | CI Job 最终状态确认 |

注：`ci_total_s` 为挂钟时间，不一定等于三个子字段之和（各子段之间可能有空隙）。

**CI 超时：** 超过 `config.timeout.ci_total_s`（默认 7200s）则停止轮询，记录已收集的部分数据，状态为 `warn`。

**成功标准（pass）：** PR 创建成功；CI 完整运行并有最终状态（`success` 或 `failed` 均为 `pass`，CI 本身通过为 `pass`，CI 失败为 `warn`）

**关键指标：**

| 字段 | 说明 |
|------|------|
| `submit_s` | PR 提交 API 调用耗时 |
| `ci_queue_s` | CI 排队时间 |
| `ci_prepare_s` | CI 准备时间 |
| `ci_run_s` | CI 运行时间 |
| `ci_total_s` | CI 总挂钟时间 |
| `ci_result` | CI 最终结果（`success`/`failed`/`timeout`） |
| `errors` | 错误信息数组 |

---

## 6. 指标输出

### JSON 报告（machine-readable）

```json
{
  "community": "cann",
  "scenario": "zero-to-custom-op",
  "timestamp": "2026-03-25T10:00:00Z",
  "cann_version": "8.0.RC1",
  "stages": {
    "learn": {
      "status": "pass",
      "search_s": 2.1,
      "official_link_rank": 1,
      "nav_hops": 2,
      "accessible_links": 45,
      "broken_links": 0,
      "errors": []
    },
    "get": {
      "status": "pass",
      "wall_clock_s": 180.5,
      "net_download_s": 165.2,
      "image_size_mb": 8200,
      "setup_steps": 5,
      "errors": []
    },
    "use": {
      "status": "pass",
      "compile_s": 45.1,
      "run_s": 2.3,
      "compile_errors": 0,
      "compile_warnings": 0,
      "run_errors": 0,
      "errors": []
    },
    "contribute": {
      "issue": {
        "status": "pass",
        "submit_s": 1.2,
        "first_response_s": 300,
        "errors": []
      },
      "pr_ci": {
        "status": "pass",
        "submit_s": 2.1,
        "ci_queue_s": 120,
        "ci_prepare_s": 45,
        "ci_run_s": 600,
        "ci_total_s": 768,
        "ci_result": "success",
        "errors": []
      }
    }
  }
}
```

### Markdown 报告模板（human-readable）

```markdown
# CANN TTFHW 测试报告

**时间：** 2026-03-25T10:00:00Z
**CANN 版本：** 8.0.RC1
**场景：** zero-to-custom-op

## 各阶段耗时汇总

| 阶段 | 状态 | 关键时间 | 备注 |
|------|------|---------|------|
| 了解 | ✅ pass | 搜索 2.1s，导航 2 跳 | 官方链接排名第1 |
| 获取 | ✅ pass | 总计 180.5s，下载 165.2s | 镜像 8200MB |
| 使用 | ✅ pass | 编译 45.1s，运行 2.3s | 无报错 |
| 贡献-Issue | ✅ pass | 提交 1.2s，首次响应 300s | — |
| 贡献-PR CI | ✅ pass | 排队 120s，准备 45s，运行 600s | CI结果: success |

## 异常记录

（无）
```

---

## 7. 对外接口

### MCP 工具

| 工具名 | 参数 | 功能 |
|--------|------|------|
| `cann_ttfhw_run_all()` | — | 运行全部阶段，返回完整报告 |
| `cann_ttfhw_run_stage(stage, substage?)` | `stage`: learn/get/use/contribute；`substage`: issue/pr_ci（仅 contribute 阶段有效，缺省则两者都跑） | 运行单个阶段或子阶段 |
| `cann_ttfhw_report(format)` | `format`: json/markdown | 获取最新报告 |

### Claude Skill

| 命令 | 功能 |
|------|------|
| `/cann-ttfhw` | 运行全部四个阶段并输出报告 |
| `/cann-learn` | 只运行了解阶段 |
| `/cann-get` | 只运行获取阶段 |
| `/cann-use` | 只运行使用阶段 |
| `/cann-contribute` | 运行贡献阶段（Issue + PR CI） |
| `/cann-contribute-issue` | 只运行贡献-Issue 子阶段 |
| `/cann-contribute-pr` | 只运行贡献-PR CI 子阶段 |

---

## 8. 设计原则

1. **可重复性：** Docker 标准化环境，每次运行结果可对比
2. **可扩展性：** Stage 接口统一，新增其他社区只需实现同一套接口，`community` 和 `scenario` 字段用于跨社区对比
3. **多维指标：** 时间 + 步骤数 + 失败次数 + 错误信息（`errors` 数组存在于每个阶段）
4. **双视角输出：** JSON 供程序消费，Markdown 供人阅读
5. **阶段隔离：** 单阶段可独立重跑，失败默认继续（可配置为终止）
6. **幂等性：** 所有提交（Issue、PR）标题含时间戳，避免重复冲突

---

## 9. config.yaml 规格

```yaml
cann_image: "ascendhub.huawei.com/public-ascendhub/ascend-toolkit:8.0.RC1"
gitcode_token: "${GITCODE_TOKEN}"   # 从环境变量注入，权限: issues:write, pull_requests:write
fork_repo: "ttfhw-bot/cann"         # 测试专用 fork，PR 从此 fork 提交
upstream_repo: "ascend/cann"        # 上游目标仓库

timeout:
  learn_s: 60
  get_s: 600
  use_s: 300
  issue_response_s: 3600
  ci_total_s: 7200

on_stage_failure: continue          # continue | abort

search:
  engine: "bing"                    # bing | google
  keywords: "Ascend CANN 快速入门"
  official_domains:
    - "gitcode.com/ascend"
    - "hiascend.com"
```
