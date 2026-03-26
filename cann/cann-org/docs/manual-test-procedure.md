# CANN TTFHW 手动测试规程

**文档版本：** v1.0
**创建日期：** 2026-03-26
**用途：** 定期手动执行，持续观测 CANN 开发者体验（TTFHW）随时间的变化

每次执行本规程，使用 `docs/manual-test-results/YYYY-MM-DD.md` 记录结果。

---

## 测试目标

测量一个新开发者从零开始使用 CANN 的端到端时间（TTFHW），识别各阶段的阻断点，持续观察：
- 官方文档是否有改善（地址变更、内容补充）
- 镜像获取路径是否变化（新版本、新地址）
- 社区响应速度是否有变化
- 每次测试与上次相比有哪些差异

---

## 测试前提条件

| 条件 | 要求 |
|------|------|
| 操作系统 | Ubuntu 20.04 / 22.04 / 24.04，x86_64 |
| Docker | 已安装，版本 ≥ 18.09 |
| 网络 | 公网可访问（不要求华为云账号） |
| Gitcode 账号 | 需要一个有效的 Personal Access Token（scope 包含 issues） |
| 本地镜像缓存 | **测试前须清除**，确保测量真实下载时间（见步骤 0） |
| 新鲜 shell | 不要在已执行过 `source set_env.sh` 的 shell 中测试 |

---

## 步骤 0：测试前准备

**目的：** 清理缓存，确保测试环境干净，模拟新用户首次操作。

```bash
# 检查并清除 CANN 相关本地镜像
docker images | grep -E "cann|ascend"
docker rmi ascendai/cann:latest quay.io/ascend/cann:latest 2>/dev/null || true

# 打开一个全新终端（不继承已有环境变量）
# 记录测试开始时间
date -u +"%Y-%m-%dT%H:%M:%SZ"
```

**记录：** 测试开始时间 `T0 = ___`

---

## 阶段一：了解阶段

**目标：** 找到 CANN 官方安装文档，获得可执行的 `docker pull` 命令。

---

### 步骤 1.1：搜索 CANN 入门文档

**操作：**
1. 打开浏览器，使用 Google 搜索：
   > `CANN 昇腾 docker 安装 入门`
2. 在搜索结果中找到 hiascend.com 的官方文档链接
3. 打开文档，等页面完全加载（SPA 需等 JS 渲染）
4. 在文档目录中找到「快速入门 → Docker 安装」章节

**检查点（记录以下信息）：**

| 检查项 | 记录 |
|--------|------|
| 找到的文档 URL | |
| 文档中的镜像拉取命令 | |
| 文档版本号（页面标题或 URL 中） | |
| 文档页面加载是否正常 | ✅ / ⚠️（加载慢）/ ❌（404 或无内容） |

**预期：** 找到包含 `docker pull` 命令的安装文档。

**记录：** 步骤 1.1 完成时间 `T1 = ___`，耗时 = `T1 - T0`

---

### 步骤 1.2：验证文档中的镜像地址可达性

**操作：**
1. 在终端中 DNS 解析文档中给出的镜像仓库地址：
   ```bash
   nslookup <文档中的镜像仓库域名>
   ```
2. 记录结果

**检查点：**

| 镜像地址 | DNS 解析结果 |
|---------|-------------|
| 文档中的主要地址 | ✅ 可达 / ❌ 解析失败 |
| 备用地址（如有） | ✅ 可达 / ❌ 解析失败 / — 无 |

**记录：** 步骤 1.2 完成时间，文档给出的镜像地址

---

## 阶段二：获取阶段

**目标：** 拉取 CANN Docker 镜像，在容器内确认版本信息。

---

### 步骤 2.1：检查 Docker 权限

**操作：**
```bash
docker info 2>&1 | grep "Server Version"
```

**检查点：**

| 检查项 | 结果 |
|--------|------|
| 能否正常输出 Server Version | ✅ / ❌ permission denied |

如果报 `permission denied`，执行修复：
```bash
# 确认用户已在 docker 组（如未在，需 sudo 加入）
grep docker /etc/group
# 激活当前 shell 中的组
newgrp docker
# 重新验证
docker info 2>&1 | grep "Server Version"
```

**记录：** 是否需要修复权限（是/否），修复耗时

---

### 步骤 2.2：执行文档中的镜像拉取命令

**操作：** 按文档执行（哪怕知道会失败，也要执行，记录实际报错）

```bash
# 替换为文档中给出的实际命令
docker pull <文档中的镜像地址>
```

**检查点：**

| 检查项 | 结果 |
|--------|------|
| 命令是否成功 | ✅ 成功 / ❌ 失败（记录报错） |
| 失败原因 | DNS 失败 / 认证失败 / 其他 |

---

### 步骤 2.3：拉取实际可用的镜像

如果步骤 2.2 失败，通过以下地址（按优先级尝试）：

| 优先级 | 镜像地址 | 登录要求 |
|--------|---------|---------|
| 1 | `ascendai/cann:latest`（Docker Hub） | 无需登录 |
| 2 | `quay.io/ascend/cann:latest` | 无需登录 |
| 3 | `swr.cn-south-1.myhuaweicloud.com/ascendhub/ascend-toolkit:latest` | 需华为云账号 |

```bash
# 记录开始时间
date -u +"%Y-%m-%dT%H:%M:%SZ"

docker pull ascendai/cann:latest

# 记录结束时间
date -u +"%Y-%m-%dT%H:%M:%SZ"
```

**检查点（记录以下信息）：**

| 检查项 | 记录 |
|--------|------|
| 实际使用的镜像地址 | |
| 镜像 Digest（sha256:...） | |
| 镜像大小（MB） | |
| 镜像创建时间 | |
| 下载耗时 | |

---

### 步骤 2.4：启动容器，验证 CANN 版本

**操作：**
```bash
# 启动容器
docker run -it --rm ascendai/cann:latest /bin/bash

# 容器内：加载环境变量
source /usr/local/Ascend/cann-*/set_env.sh

# 查看 CANN 版本
ls /usr/local/Ascend/
cat /usr/local/Ascend/cann-*/x86_64-linux/ascend_toolkit_install.info
```

**检查点（记录以下信息）：**

| 检查项 | 记录 |
|--------|------|
| CANN 版本号（version=） | |
| 安装路径（path=） | |
| 支持架构 | |
| `set_env.sh` 路径 | |

**记录：** 阶段二完成时间 `T2 = ___`，获取阶段耗时 = `T2 - T1`

---

## 阶段三：使用阶段

**目标：** 在容器内运行 CANN 提供的工具，验证开发工具链可用。

---

### 步骤 3.1：验证 ATC 工具（不依赖 NPU 硬件）

**操作（容器内）：**
```bash
source /usr/local/Ascend/cann-*/set_env.sh
which atc
atc --help 2>&1 | head -5
```

**检查点：**

| 检查项 | 结果 |
|--------|------|
| `atc` 命令存在 | ✅ / ❌ |
| `atc --help` 正常输出 | ✅ / ❌ |

---

### 步骤 3.2：尝试运行 AscendCL Hello World（记录是否需要硬件）

**操作（容器内）：**
```bash
python3 -c "
import sys
sys.path.insert(0, '/usr/local/Ascend/ascend-toolkit/latest/python/site-packages')
import acl
ret = acl.init()
print(f'acl.init() ret={ret}')
if ret == 0:
    print('Hello World from AscendCL!')
    acl.finalize()
else:
    print('需要 NPU 硬件')
"
```

**检查点：**

| 检查项 | 结果 |
|--------|------|
| `acl.init()` 返回值 | `0`（成功）/ 非零（需硬件） |
| 是否输出 Hello World | ✅ / ❌（记录具体返回码） |
| 无 NPU 时替代验证 | `atc --help` 正常 ✅ |

**记录：** 阶段三完成时间 `T3 = ___`，使用阶段耗时 = `T3 - T2`

---

## 阶段四：贡献阶段

**目标：** 向 CANN 社区提交一个真实的 issue，测量社区响应时间。

---

### 步骤 4.1：找到 CANN 社区仓库

**操作：** 打开浏览器，访问 [gitcode.com/cann](https://gitcode.com/cann)，找到 `community` 仓库。

**当前已知地址：**
- Gitcode 社区仓库：[gitcode.com/cann/community](https://gitcode.com/cann/community)
- Issues 接口：`POST https://api.gitcode.com/api/v5/repos/cann/community/issues`

**检查点：**

| 检查项 | 记录 |
|--------|------|
| community 仓库是否仍然存在 | ✅ / ❌（记录新地址） |
| issues 是否开放 | ✅ / ❌ |

---

### 步骤 4.2：提交真实 Issue

**要求：**
- 必须是真实遇到的问题，不能是测试占位 issue
- 内容要有实际价值（文档问题、安装报错、工具链缺失等）
- 记录提交时间和 issue 编号

**本次测试中发现的候选问题（每次测试时选一个或补充新发现的）：**

| 问题 | 建议 issue 标题 |
|------|---------------|
| `ascendhub.huawei.com` DNS 失败 | 快速入门文档 ascendhub 域名公网不可解析，建议补充 Docker Hub 替代地址 |
| 文档是 SPA，内容加载慢 | 官方文档建议提供静态版本或 PDF，方便离线查阅 |
| `cann-info` 命令在 9.0 容器中不存在 | 9.0 镜像中 cann-info 命令缺失，文档中仍引用该命令 |
| 新用户对 cann 组织结构不了解 | 建议在快速入门文档中明确 Gitcode 社区仓库地址 |

**操作：**
```bash
# 记录提交时间
date -u +"%Y-%m-%dT%H:%M:%SZ"

curl -X POST "https://api.gitcode.com/api/v5/repos/cann/community/issues" \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "<YOUR_GITCODE_TOKEN>",
    "title": "<本次测试发现的真实问题标题>",
    "body": "<详细描述：问题现象、复现步骤、环境信息、建议>"
  }'
```

**检查点（记录以下信息）：**

| 检查项 | 记录 |
|--------|------|
| Issue 编号 | #___ |
| Issue URL | |
| 提交时 API 响应耗时（ms） | |
| HTTP 状态码 | |

---

### 步骤 4.3：等待社区响应（24~72 小时后回查）

**操作（24 小时后）：**
```bash
curl "https://api.gitcode.com/api/v5/repos/cann/community/issues/<ISSUE_NUMBER>/comments?access_token=<TOKEN>"
```

**检查点：**

| 检查项 | 记录 |
|--------|------|
| 是否有回复 | ✅ 有回复 / ❌ 无回复（记录等待时间） |
| 首次回复时间 | |
| 首次响应耗时（从提交到第一条回复） | |
| 回复内容类型 | 机器人自动回复 / 人工回复 / 无 |

**记录：** 阶段四完成时间 `T4 = ___`（提交 issue 完成，不含等待响应）

---

## 时间汇总模板

每次测试填写以下表格（复制到结果文件）：

```
测试日期：YYYY-MM-DD
测试人：
环境：OS / Docker 版本

| 阶段 | 开始时间 | 结束时间 | 耗时 | 状态 | 备注 |
|------|---------|---------|------|------|------|
| 了解 | T0      | T1      |      |      |      |
| 获取 | T1      | T2      |      |      |      |
| 使用 | T2      | T3      |      |      |      |
| 贡献 | T3      | T4      |      |      |      |
| 全流程 | T0     | T4      |      |      |      |

TTFHW（到工具链可用）= T0 → atc --help 成功

镜像信息：
- 实际使用地址：
- 版本：
- 下载耗时：

Issue：
- 编号：
- URL：
- 提交耗时（API）：
- 首次响应耗时：
```

---

## 观测指标与优化判断标准

每次测试后，与上次结果对比以下指标：

### 官方文档（了解阶段）

| 指标 | 优化标准 |
|------|---------|
| 文档 URL 稳定性 | URL 未变更 = 好；变更需更新规程 |
| 镜像地址可达性 | `ascendhub.huawei.com` DNS 可解析 = 有改善 |
| 文档是否补充 Docker Hub 替代地址 | 新增说明 = 有改善 |
| 页面加载时间 | 较上次缩短 = 有改善 |

### 镜像获取（获取阶段）

| 指标 | 优化标准 |
|------|---------|
| 镜像版本 | 有新版本发布（记录版本号变化） |
| 镜像大小 | 减小 = 有改善 |
| 下载速度（MB/s） | 提升 = 有改善 |
| 官方地址可用性 | `ascendhub` 或 SWR 无需登录即可拉取 = 有改善 |

### 工具链（使用阶段）

| 指标 | 优化标准 |
|------|---------|
| `acl.init()` 无需 NPU 可运行 | 新版本支持 CPU 模拟 = 有改善 |
| `cann-info` 命令可用 | 命令存在且输出版本 = 有改善（当前缺失） |
| set_env.sh 路径稳定 | 路径未变化 = 好 |

### 社区响应（贡献阶段）

| 指标 | 优化标准 |
|------|---------|
| Issue 提交成功率 | 100% = 好 |
| 首次响应耗时 | 缩短 = 有改善 |
| 响应类型 | 人工回复 > 机器人回复 |

---

## 历史测试记录索引

| 日期 | 结果文件 | TTFHW | 镜像版本 | Issue | 首次响应耗时 |
|------|---------|-------|---------|-------|------------|
| 2026-03-26 | [test-run-manual-2026-03-26.md](../reports/test-run-manual-2026-03-26.md) | ~30~38min | 9.0.0-beta.1 | [#95](https://gitcode.com/cann/community/issues/95) | 待观测 |
