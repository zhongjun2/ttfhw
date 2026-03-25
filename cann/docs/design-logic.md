# TTFHW CANN 框架设计逻辑

记录框架的核心设计思路、架构决策和各阶段定义。

---

## 项目目标

构建一套**可重复执行、自动化、多维指标**的测试框架，衡量开发者在 Ascend CANN 社区经历四个阶段（了解/获取/使用/贡献）的时间成本和体验质量，用于后续与其他 AI 框架社区（CUDA、ROCm 等）横向对比。

---

## 核心场景

**端到端全链路：从零到第一个自定义算子**

> 模拟一个全新开发者：找到CANN文档 → 拉取环境 → 编写运行自定义算子 → 向社区贡献并查看CI结果

---

## 架构设计

### 目录结构

```
ttfhw-cann/
├── runner.py                  # 主入口，串联执行各阶段
├── stages/
│   ├── base.py                # Stage基类，统一接口
│   ├── stage_learn.py         # 阶段1：了解
│   ├── stage_get.py           # 阶段2：获取
│   ├── stage_use.py           # 阶段3：使用
│   └── stage_contribute.py    # 阶段4：贡献（含CI追踪）
├── metrics/
│   └── collector.py           # 统一指标收集器
├── reports/
│   └── reporter.py            # 输出JSON + Markdown报告
├── fixtures/
│   └── custom_op/             # 标准测试算子代码（AddCustom）
├── mcp_server.py              # MCP服务入口
├── skills/                    # Claude Skill定义
└── config.yaml                # 配置（Docker镜像版本、超时、token等）
```

### Stage 统一接口

每个Stage模块实现：
```python
class BaseStage:
    def setup(self)    # 准备环境
    def run(self)      # 执行操作
    def verify(self)   # 验证成功
    def teardown(self) # 清理环境
    def metrics(self)  # 返回收集的指标
```

Runner依次调用，某阶段失败可配置为跳过或终止。

---

## 四个阶段详细定义

### 阶段1：了解（Learn）

**自动化内容：**
- 调用搜索工具（Bing/Google）搜索关键词（如 "Ascend CANN 快速入门"）
- 从搜索结果中识别官方主页/Gitcode仓库链接
- 从主页导航到快速入门文档
- 抓取关键资源链接（安装指南、API文档、示例代码）
- 验证链接可达性

**成功标准：**
- 搜索结果中能找到官方链接
- 快速入门页可访问
- 关键API文档存在且可达

**关键指标：**
- 搜索耗时
- 官方链接在搜索结果中的排名（第几条）
- 从搜索到找到快速入门的跳转次数
- 可访问链接数
- 断链数量

---

### 阶段2：获取（Get）

**自动化内容：**
- 拉取官方CANN Docker镜像
- 启动容器，验证环境变量和工具链
- 运行 `cann-info` 或等效命令确认版本

**成功标准：**
- Docker镜像拉取成功
- 容器内CANN工具链可用，版本信息可读

**关键指标：**
- 挂钟时间（含下载）
- 净下载时间
- 镜像大小
- 环境验证步骤数

---

### 阶段3：使用（Use）

**自动化内容：**
- 在容器内使用fixtures中的标准自定义算子代码（TBE AddCustom算子）
- 编译算子
- 运行算子推理
- 验证输出与参考值误差在阈值内

**成功标准：**
- 算子编译通过
- 运行输出与参考值误差 < 阈值（如1e-5）

**关键指标：**
- 编译时间
- 运行时间
- 编译报错次数
- 运行报错次数

---

### 阶段4：贡献（Contribute）

分为两个子阶段：

#### 4a. 基础贡献：提交Issue
**自动化内容：**
- 向CANN社区Gitcode仓库提交标准化测试Issue
- 记录Issue编号和提交时间
- 轮询检测首次响应时间

**成功标准：**
- Issue成功创建，返回Issue编号

**关键指标：**
- Issue提交耗时
- 首次响应时间（机器人/人工）

#### 4b. 高级贡献：提交PR并追踪CI
**自动化内容：**
- 向CANN社区提交标准化测试PR（使用fixtures中的算子代码）
- 监听PR的CI流水线状态
- 分阶段记录CI各环节时间

**成功标准：**
- PR成功创建
- CI流水线触发并完成（Pass或Fail均记录）

**关键指标：**
- PR提交耗时
- CI排队时间（从提交到CI开始运行）
- CI准备时间（环境初始化）
- CI运行时间（实际检查/构建/测试）
- CI总耗时

---

## 指标输出格式

### JSON报告（machine-readable）
```json
{
  "community": "cann",
  "timestamp": "2026-03-25T10:00:00Z",
  "scenario": "zero-to-custom-op",
  "stages": {
    "learn": {
      "status": "pass",
      "wall_clock_s": 12.3,
      "accessible_links": 45,
      "broken_links": 2,
      "nav_depth": 3
    },
    "get": {
      "status": "pass",
      "wall_clock_s": 180.5,
      "net_download_s": 165.2,
      "image_size_mb": 8200,
      "setup_steps": 5
    },
    "use": {
      "status": "pass",
      "compile_s": 45.1,
      "run_s": 2.3,
      "compile_errors": 0,
      "run_errors": 0
    },
    "contribute": {
      "issue": {
        "status": "pass",
        "submit_s": 1.2,
        "first_response_s": 300
      },
      "pr_ci": {
        "status": "pass",
        "submit_s": 2.1,
        "ci_queue_s": 120,
        "ci_prepare_s": 45,
        "ci_run_s": 600,
        "ci_total_s": 765
      }
    }
  }
}
```

### Markdown报告（human-readable）
供Claude展示给开发者或写入文档。

---

## MCP工具接口

```python
# 运行全部阶段
cann_ttfhw_run_all()

# 运行单个阶段
cann_ttfhw_run_stage(stage: "learn" | "get" | "use" | "contribute")

# 获取最新报告
cann_ttfhw_report(format: "json" | "markdown")
```

## Claude Skill接口

| Skill命令 | 功能 |
|----------|------|
| `/cann-ttfhw` | 运行全部四个阶段并输出报告 |
| `/cann-learn` | 只运行了解阶段 |
| `/cann-get` | 只运行获取阶段 |
| `/cann-use` | 只运行使用阶段 |
| `/cann-contribute` | 只运行贡献阶段（含CI追踪） |

---

## 设计原则

1. **可重复性**：每次运行结果可对比，环境通过Docker标准化
2. **可扩展性**：Stage接口统一，新增其他社区（ROCm、CUDA）只需实现同一套接口
3. **多维指标**：不只是时间，还有步骤数、失败次数、错误信息
4. **双视角输出**：JSON供程序消费和横向对比，Markdown供人阅读
