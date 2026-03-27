# CANN 手动评估 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude 扮演新用户，通过 Google 搜索 → 读文档 → 执行命令，完成 CANN 安装和 Qwen2 推理，并输出带出处引用的中文评估报告。

**Architecture:** 顺序执行 3 个阶段（了解 → 获取 → 使用），每步操作附来源注释，最终汇总为 Markdown 报告。无代码工具，仅使用 WebSearch / WebFetch / Bash。

**Tech Stack:** WebSearch（Google）、WebFetch（网页内容读取）、Bash（shell 命令执行）、Markdown（报告格式）

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `cann-manual/eval-protocol.md` | 新建 | 可复用的评估执行指南（人类或 Claude 下次直接按此操作） |
| `cann-manual/reports/2026-03-27.md` | 新建 | 本次评估的完整中文报告 |

---

## Task 1：写 eval-protocol.md（评估协议文件）

**Files:**
- Create: `cann-manual/eval-protocol.md`

- [ ] **Step 1：写协议文件**

内容如下（逐字写入，不省略）：

```markdown
# CANN 易用性评估协议 v1.0

> 本协议供 Claude 或人工测试员使用。执行时严格按步骤顺序操作，每步必须注明来源。

## 执行规则

1. **来源引用**：每步操作后附一条来源注释：
   `来源：<URL> → 《文章标题》→「具体段落/章节描述」`
2. **计时**：每阶段开始和结束时执行 `date +%s` 记录时间戳，报告中换算为分钟。
3. **断点记录**：遇到错误，先尝试按文档方法解决；解决不了则记为断点（P0/P1/P2），继续后续步骤。
4. **不得修改逻辑**：执行命令必须来自找到的文档原文，仅允许补充运行环境参数（需注明）。

---

## 阶段一：了解（Learn）

**目标**：找到 CANN 官方安装文档、Quick Start 链接、Qwen2 部署文档，验证链接可访问。

| 步骤 | 操作 | 预期结果 |
|------|------|---------|
| L1 | Google 搜索 `"CANN 昇腾 安装"` | 返回至少 5 条结果 |
| L2 | 找 `hiascend.com` 官方链接，记录排名 | 有 / 无，第几条 |
| L3 | 打开官方链接，进入文档中心，找安装页面入口 | 找到安装文档 URL |
| L4 | 在文档网站内导航，找 Quick Start 页面链接 | 找到 Quick Start URL |
| L5 | Google 搜索 `"Qwen2 CANN 昇腾 推理"` | 找到 Qwen2 部署文档 URL |
| L6 | 逐一 HTTP 检查找到的链接是否可访问 | 记录 accessible / broken |

---

## 阶段二：获取（Get）

**目标**：按文档说明拉取 CANN Docker 镜像，验证 atc 工具链可用。

| 步骤 | 操作 | 预期结果 |
|------|------|---------|
| G1 | 从 Quick Start 文档提取 docker pull 命令及镜像名 | 记录命令原文和来源 |
| G2 | 执行 `docker pull <image>` | 镜像拉取成功 |
| G3 | 按文档启动容器，执行 `atc --help` 验证工具链 | 退出码 0 |

---

## 阶段三：使用（Use）

**目标**：按文档完成 Quick Start 验证，再按 Qwen2 部署文档完成推理。

| 步骤 | 操作 | 预期结果 |
|------|------|---------|
| U1 | 从 Quick Start 文档提取示例命令并执行 | 命令正常运行 |
| U2 | 从 Qwen2 部署文档提取依赖安装命令 | pip install 成功 |
| U3 | 按文档下载 Qwen2 模型 | 模型文件下载完成 |
| U4 | 按文档执行推理命令 | 有推理输出 |

---

## 报告模板

执行完成后，将记录汇总填入 `reports/YYYY-MM-DD.md`，结构见设计规格：
`docs/superpowers/specs/2026-03-27-cann-manual-design.md` § 七
```

- [ ] **Step 2：验证文件写入**

```bash
wc -l cann-manual/eval-protocol.md
```

预期输出：行数 > 50

- [ ] **Step 3：提交**

```bash
git add cann-manual/eval-protocol.md
git commit -m "docs(cann-manual): add reusable evaluation protocol v1.0"
```

---

## Task 2：执行阶段一——了解（Learn）

**Files:**
- Create: `cann-manual/reports/2026-03-27.md`（初始化，持续追加）

- [ ] **Step 1：记录阶段开始时间**

```bash
date +%s && date "+%Y-%m-%d %H:%M:%S"
```

记录输出的时间戳（unix 秒数）和可读时间，写入报告草稿。

- [ ] **Step 2：搜索 "CANN 昇腾 安装"**

执行 WebSearch，关键词：`CANN 昇腾 安装`

记录：
- 返回的结果条数
- 每条结果的 URL + 标题
- `hiascend.com` 是否出现，第几条

- [ ] **Step 3：打开官方链接，找安装文档入口**

对 L2 找到的 `hiascend.com` 链接（若有）执行 WebFetch。若 L2 未找到官方链接，直接访问 `https://www.hiascend.com` 并记录为断点 P1（Google 搜索未返回官网）。

在页面内容中找到"安装"或"下载"相关的链接，记录 URL 和来源段落。

- [ ] **Step 4：找 Quick Start 链接**

在安装文档页面内导航，找 Quick Start 或快速入门链接。若当前页面无法导航，搜索 `site:hiascend.com CANN quick start 快速入门`。

记录找到的 Quick Start URL。

- [ ] **Step 5：搜索 Qwen2 部署文档**

执行 WebSearch，关键词：`Qwen2 CANN 昇腾 推理`

记录找到的最相关文档 URL + 标题。

- [ ] **Step 6：验证所有链接可访问**

对找到的每个 URL 执行 WebFetch（仅读取首屏内容以确认可访问）。

记录每个 URL 的状态：accessible（有正常内容）或 broken（报错/空白）。

- [ ] **Step 7：记录阶段结束时间，写入报告**

```bash
date +%s && date "+%Y-%m-%d %H:%M:%S"
```

计算耗时（end - start 秒数，换算为分钟）。

初始化报告文件，写入了解阶段内容：

```bash
cat > cann-manual/reports/2026-03-27.md << 'REPORT_EOF'
# CANN 易用性评估报告

**测试日期：** 2026-03-27
**测试方式：** Claude 模拟新用户手动执行
**环境：** （执行时填入 uname -a 输出）

---

## 总览

| 阶段 | 状态 | 耗时 |
|------|------|------|
| 了解 | （填入） | （填入） |
| 获取 | （填入） | （填入） |
| 使用 | （填入） | （填入） |

---

## 阶段一：了解

（填入搜索过程、找到的链接、断点）
REPORT_EOF
```

- [ ] **Step 8：提交阶段一结果**

```bash
git add cann-manual/reports/2026-03-27.md
git commit -m "docs(cann-manual): add learn phase results to 2026-03-27 report"
```

---

## Task 3：执行阶段二——获取（Get）

**Files:**
- Modify: `cann-manual/reports/2026-03-27.md`（追加获取阶段内容）

- [ ] **Step 1：记录阶段开始时间**

```bash
date +%s && date "+%Y-%m-%d %H:%M:%S"
```

- [ ] **Step 2：从 Quick Start 文档提取 docker 命令**

对 Task 2 Step 4 找到的 Quick Start URL 执行 WebFetch，找到以下内容：
- docker pull 命令原文（含镜像名）
- 启动容器的命令原文

记录命令原文和来源（URL + 章节名 + 具体段落引用）。

- [ ] **Step 3：执行 docker pull**

执行文档中找到的 docker pull 命令：

```bash
date +%s  # 记录下载开始时间
docker pull <文档中找到的镜像名>
date +%s  # 记录下载结束时间
```

记录：
- 镜像名（原文）
- 下载耗时（秒）
- 镜像大小（`docker images` 查看）

如果拉取失败，记为断点（现象 + 原因），尝试文档中提及的替代镜像，若文档无替代方案则记为 P0 断点。

- [ ] **Step 4：启动容器，执行 atc --help**

按文档中找到的容器启动命令执行：

```bash
# 按文档原文启动容器（示例，以文档实际内容为准）
docker run -it --rm <镜像名> bash -c "source /usr/local/Ascend/cann-*/set_env.sh && atc --help" 2>&1 | head -20
echo "exit code: $?"
```

记录：
- 退出码
- 输出前 200 字符
- CANN 版本（从输出或 `/usr/local/Ascend/cann-*/` 目录名提取）

- [ ] **Step 5：记录阶段结束时间，更新报告**

```bash
date +%s && date "+%Y-%m-%d %H:%M:%S"
```

在 `reports/2026-03-27.md` 追加获取阶段内容（docker 命令来源、执行结果、耗时、断点）。

- [ ] **Step 6：提交**

```bash
git add cann-manual/reports/2026-03-27.md
git commit -m "docs(cann-manual): add get phase results to 2026-03-27 report"
```

---

## Task 4：执行阶段三——使用 Quick Start（Use / Quick Start）

**Files:**
- Modify: `cann-manual/reports/2026-03-27.md`

- [ ] **Step 1：记录子阶段开始时间**

```bash
date +%s && date "+%Y-%m-%d %H:%M:%S"
```

- [ ] **Step 2：从 Quick Start 文档提取示例命令**

对 Quick Start URL 执行 WebFetch（或复用 Task 3 Step 2 的结果），找到：
- Quick Start 的核心示例命令（如 ATC 模型转换示例、hello world 等）
- 命令执行前提条件

记录命令原文和来源。

- [ ] **Step 3：在容器内执行 Quick Start 示例**

```bash
docker run -it --rm <镜像名> bash -c "
source /usr/local/Ascend/cann-*/set_env.sh
<文档中找到的 Quick Start 示例命令>
echo exit_code: \$?
" 2>&1
```

记录输出和退出码。

- [ ] **Step 4：记录结束时间，更新报告**

在 `reports/2026-03-27.md` 追加 Quick Start 小节（命令来源、执行结果、耗时、断点）。

---

## Task 5：执行阶段三——Qwen2 推理（Use / Qwen2）

**Files:**
- Modify: `cann-manual/reports/2026-03-27.md`

- [ ] **Step 1：记录子阶段开始时间**

```bash
date +%s && date "+%Y-%m-%d %H:%M:%S"
```

- [ ] **Step 2：从 Qwen2 部署文档提取操作步骤**

对 Task 2 Step 5 找到的 Qwen2 部署文档 URL 执行 WebFetch，找到：
- 依赖安装命令（pip install ...）
- 模型下载命令
- 推理示例代码

记录每条命令的原文和来源（URL + 章节 + 段落）。

- [ ] **Step 3：创建 venv，安装依赖**

```bash
date +%s  # pip 安装开始
python3 -m venv /tmp/cann_manual_venv
source /tmp/cann_manual_venv/bin/activate
pip install <文档中找到的依赖列表>
date +%s  # pip 安装结束
echo "exit code: $?"
```

记录安装耗时和退出码。若安装失败，记录断点并继续。

- [ ] **Step 4：下载 Qwen2 模型**

```bash
date +%s  # 下载开始
<文档中找到的模型下载命令>
date +%s  # 下载结束
# 统计模型大小
du -sh <模型目录> 2>/dev/null || echo "目录不存在"
```

记录下载耗时和模型大小。

- [ ] **Step 5：执行推理**

```bash
date +%s  # 推理开始
source /tmp/cann_manual_venv/bin/activate
python3 -c "
<文档中找到的推理示例代码>
"
date +%s  # 推理结束
echo "exit code: $?"
```

记录推理输出、退出码、耗时。若失败，记录断点（现象 + 原因 + 解决尝试）。

- [ ] **Step 6：清理 venv**

```bash
deactivate 2>/dev/null || true
rm -rf /tmp/cann_manual_venv
```

---

## Task 6：汇总写完整报告

**Files:**
- Modify: `cann-manual/reports/2026-03-27.md`（最终版本）

- [ ] **Step 1：查看环境信息**

```bash
uname -a
python3 --version
docker --version
```

- [ ] **Step 2：将全程记录汇总，改写为完整报告**

将 `reports/2026-03-27.md` 改写为完整版，结构如下：

```markdown
# CANN 易用性评估报告

**测试日期：** 2026-03-27
**测试方式：** Claude 模拟新用户手动执行
**环境：** <uname -a 输出>

---

## 总览

| 阶段 | 状态 | 耗时 |
|------|------|------|
| 了解 | ✅/❌ | Xm Ys |
| 获取（Docker） | ✅/❌ | Xm Ys |
| 使用（Quick Start） | ✅/❌ | Xm Ys |
| 使用（Qwen2 推理） | ✅/❌ | Xm Ys |

## 本次测试引用的文档来源
- [文章标题](URL) — 用于阶段X步骤Y

---

## 阶段一：了解

### 搜索过程
- **关键词：** "CANN 昇腾 安装"
- **hiascend.com 排名：** 第X条 / 未找到
- **耗时：** Xm Ys

### 找到的链接清单
| 链接 | 标题 | 可访问 |
|------|------|--------|

### 断点
（若有）

---

## 阶段二：获取

### Docker 安装
**命令来源：**
> 来源：<URL> → 《文章标题》→「具体段落」

**执行过程：**
- `docker pull` 耗时：Xs，镜像大小：X MB
- `atc --help` 退出码：0，CANN 版本：X.X.X

**断点：**（若有）

---

## 阶段三：使用

### Quick Start 验证
**命令来源：**
> 来源：<URL> → 《文章标题》→「具体段落」

**执行结果：** ✅/❌
**耗时：** Xs

### Qwen2 推理
**依赖安装来源：**
> 来源：<URL> → 《文章标题》→「具体段落」

| 步骤 | 耗时 | 结果 |
|------|------|------|
| pip install | Xs | ✅/❌ |
| 模型下载（X MB） | Xs | ✅/❌ |
| 推理执行 | Xs | ✅/❌ |

**推理输出：** `<输出内容>`

**断点：**（若有）

---

## 断点汇总

| 编号 | 阶段 | 严重程度 | 现象 | 原因 | 解决方案 |
|------|------|---------|------|------|---------|
```

- [ ] **Step 3：最终提交**

```bash
git add cann-manual/reports/2026-03-27.md
git commit -m "docs(cann-manual): add complete 2026-03-27 evaluation report"
```

---

## Self-Review 检查清单

- [x] **Spec 覆盖**：L1-L6（了解）、G1-G3（获取）、U1-U4（使用）全部有对应 Task
- [x] **来源引用**：每个执行步骤均要求记录 URL + 章节 + 段落来源
- [x] **计时**：每阶段用 `date +%s` 记录起止时间
- [x] **断点格式**：现象 / 原因 / 解决方案 / 严重程度
- [x] **报告模板**：Task 6 提供完整报告骨架，无占位符
- [x] **无 TBD/TODO**：命令中的 `<文档中找到的内容>` 是运行时动态填入，非设计时占位符
- [x] **顺序依赖**：Task 2 → 3 → 4 → 5 → 6，依赖关系明确
