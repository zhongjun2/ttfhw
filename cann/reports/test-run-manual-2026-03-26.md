# CANN TTFHW 手动测试报告

**测试类型：** 手动模拟（逐步执行，记录每个操作）
**执行时间：** 2026-03-26T06:53:58Z — 2026-03-26T07:04:35Z
**执行机器：** Linux 6.8.0-59-generic (Ubuntu 24.04), x86_64
**执行用户：** zhongjun
**Shell：** bash

---

## 一、了解阶段

**开始时间：** 06:53:58Z

---

### 操作 1：打开浏览器，搜索 CANN 怎么用

**时间：** 06:53:58Z
**动作：** 在 Google 搜索框输入：`CANN 昇腾 怎么开始用 入门`

**搜索结果中看到：**
- 华为昇腾官方文档入口：[hiascend.com/document/detail/zh/CANNCommunityEdition](https://www.hiascend.com/document/detail/zh/CANNCommunityEdition)
- 昇腾社区论坛：[bbs.huaweicloud.com/ascend](https://bbs.huaweicloud.com/ascend)
- GitHub 示例代码：[github.com/Ascend/samples](https://github.com/Ascend/samples)

**得到的关键信息：**
- CANN = Compute Architecture for Neural Networks，华为 AI 计算架构
- 主要组件：AscendCL、ATC（模型转换）、CCEC（编译器）
- 推荐安装方式：Docker 镜像

**耗时：** ~39s（06:53:58Z → 06:54:37Z）

---

### 操作 2：访问官方文档，找 Docker 安装方法

**时间：** 06:54:37Z
**动作：** 继续搜索 `site:hiascend.com CANN 社区版 docker 安装 quickstart 2025`

**找到文档：**
- Docker 快速安装指南：[hiascend.com/document/detail/zh/CANNCommunity/80RC3alpha002/quickstart/quickstart/quickstart_18_0002.html](https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/80RC3alpha003/quickstart/quickstart/quickstart_18_0001.html)

**文档中的安装命令：**
```bash
# 官方文档给出的主要拉取命令
docker pull ascendhub.huawei.com/public-ascendhub/ascend-toolkit:latest
```

**耗时：** ~42s（06:54:37Z → 06:55:19Z）

---

### 了解阶段小结

| 指标 | 值 |
|------|-----|
| 搜索次数 | 2次 |
| 找到文档入口 | ✅ [CANN 社区版快速入门](https://www.hiascend.com/document/detail/zh/CANNCommunityEdition/80RC3alpha003/quickstart/quickstart/quickstart_18_0001.html) |
| 文档可访问 | ✅（但是 SPA，内容靠搜索摘要了解） |
| 获得安装命令 | ✅ `docker pull ascendhub.huawei.com/...` |
| **了解阶段总耗时** | **~81s（约 1min 21s）** |
| **状态** | ⚠️ warn（文档为 SPA，内容无法自动提取） |

---

## 二、获取阶段

**开始时间：** 06:55:19Z

---

### 操作 3：检查 Docker 是否安装

**时间：** 06:55:19Z
**动作：** 打开终端，输入：

```bash
docker --version
```

**输出：**
```
Docker version 29.2.1, build a5c7197
```

**判断：** Docker 29.2.1，满足 ≥18.09 的要求，继续下一步。
**耗时：** <1s

---

### 操作 4：确认 Docker 权限

**时间：** 06:55:20Z
**动作：**

```bash
id
```

**输出：**
```
uid=1001(zhongjun) gid=1001(zhongjun) groups=1001(zhongjun)
```

发现没有 `docker` 组，继续测试一下：

```bash
docker info 2>&1 | grep -E "Server Version|permission|ERROR"
```

**输出：**
```
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

**问题：** 当前用户不在 docker 组，无法访问 Docker。

---

### 操作 5：修复 Docker 权限

**时间：** 06:55:25Z
**动作：** 查看 docker 组现状：

```bash
grep docker /etc/group
ls -la /var/run/docker.sock
```

**输出：**
```
docker:x:988:zhongjun
srw-rw---- 1 root docker 0 Feb  3 10:38 /var/run/docker.sock
```

`/etc/group` 显示 zhongjun 已经在 docker 组里，但当前 shell 的组列表没有更新。

**动作：** 用 `newgrp` 激活新组：

```bash
newgrp docker
id
```

**输出：**
```
uid=1001(zhongjun) gid=988(docker) groups=988(docker),1001(zhongjun)
```

再次验证 Docker 可用：

```bash
docker info 2>&1 | grep "Server Version"
```

**输出：**
```
 Server Version: 29.2.1
```

**结果：** ✅ Docker 权限修复完成。
**耗时：** ~50s

---

### 操作 6：按文档命令拉取镜像（ascendhub）

**时间：** 06:56:08Z
**动作：** 执行文档中给出的官方命令：

```bash
docker pull ascendhub.huawei.com/public-ascendhub/ascend-toolkit:latest
```

**输出：**
```
Error response from daemon: failed to resolve reference
"ascendhub.huawei.com/public-ascendhub/ascend-toolkit:latest":
failed to do request: Head "https://ascendhub.huawei.com/v2/...":
dial tcp: lookup ascendhub.huawei.com on 127.0.0.53:53: no such host
```

**问题：** `ascendhub.huawei.com` DNS 解析失败，该域名是华为内部域名，公网无法访问。
**耗时：** <1s（立即报错）

---

### 操作 7：搜索可替代的公开镜像地址

**时间：** 06:56:10Z
**动作：** 搜索 `ascend CANN docker image public pull without login quay.io ghcr.io 2025`

**搜索结果关键信息：**
- Docker Hub 上有 `ascendai/cann` 公开镜像（不需要登录）
- quay.io 上有 `quay.io/ascend/cann` 公开镜像
- Huawei SWR (`swr.cn-south-1.myhuaweicloud.com`) 需要华为云账号登录

**耗时：** ~37s（06:56:10Z → 06:56:47Z）

---

### 操作 8：拉取 Docker Hub 公开镜像

**时间：** 06:56:47Z
**动作：**

```bash
docker pull ascendai/cann:latest
```

**输出（实时）：**
```
latest: Pulling from ascendai/cann
Digest: sha256:a05cfa0b1c2232e1c9f631f0b65765746e0d0b5c8ea40d163f42aeecc853354b
Status: Downloaded newer image for ascendai/cann:latest
docker.io/ascendai/cann:latest
```

**结果：** ✅ 下载成功。
**镜像大小：** 4,280,110,483 bytes（约 4.08 GB）
**镜像创建时间：** 2026-03-11T09:20:05Z
**耗时：** 约 18s（已有本地缓存，上次会话已下载，本次命中缓存直接完成）

> **说明：** 本次测试中 `ascendai/cann:latest` 与前一次测试拉取的 `quay.io/ascend/cann:latest` 是同一镜像（Digest 相同），Docker 命中本地缓存，无需重新下载。如果是第一次拉取约需 6min。

---

### 操作 9：启动容器并验证 CANN 安装

**时间：** 06:57:05Z
**动作：**

```bash
docker run -d --rm ascendai/cann:latest sleep 120
```

**输出：**
```
1cf8513693e67b63f0eb95a47881a833789b63da0d3a5f05f98ba60509dc4d7f
```

验证 CANN 版本文件：

```bash
docker exec <container> cat /usr/local/Ascend/cann-9.0.0-beta.1/x86_64-linux/ascend_toolkit_install.info
```

**输出：**
```
package_name=Ascend-cann-toolkit
version=9.0.0-beta.1
innerversion=V100R001C10B034
compatible_version=[V100R001C15],[V100R001C19],[V100R001C20],[V100R001C21],[V100R001C23],[V100R001C10]
arch=x86_64
os=linux
path=/usr/local/Ascend/cann-9.0.0-beta.1
```

验证核心工具 ATC 可用：

```bash
docker exec <container> bash -c '
source /usr/local/Ascend/cann-9.0.0-beta.1/set_env.sh
atc --help 2>&1 | head -3
'
```

**输出：**
```
ATC start working now, please wait for a moment.
usage: atc <args>
generate offline model example:
```

**结果：** ✅ CANN 9.0.0-beta.1 安装正常，ATC 工具可用。
**耗时：** ~18s（06:57:05Z → 06:57:23Z）

---

### 获取阶段小结

| 步骤 | 操作 | 耗时 | 结果 |
|------|------|------|------|
| 操作 3 | 检查 Docker 版本 | <1s | ✅ |
| 操作 4 | 确认 Docker 权限 | <1s | ❌（需要修复） |
| 操作 5 | 激活 docker 组（newgrp） | ~50s | ✅ |
| 操作 6 | docker pull ascendhub（官方） | <1s | ❌ DNS 失败 |
| 操作 7 | 搜索公开替代镜像 | ~37s | ✅ 找到 ascendai/cann |
| 操作 8 | docker pull ascendai/cann:latest | ~18s（命中缓存） | ✅ |
| 操作 9 | 启动容器，验证 CANN | ~18s | ✅ |
| **获取阶段总耗时** | | **~2min 4s** | ✅ |
| **状态** | | | ✅ pass |

> **注：** 首次拉取（无缓存）需 ~6min 下载 4.08 GB 镜像。

---

## 三、使用阶段

**开始时间：** 06:57:23Z

---

### 操作 10：搜索 CANN Hello World 示例

**时间：** 06:57:23Z
**动作：** 搜索 `CANN AscendCL hello world 示例 acl python 无NPU CPU模式运行`

**搜索结果关键信息：**
- 官方示例仓库：[gitee.com/ascend/samples](https://gitee.com/ascend/samples)
- AscendCL Python Hello World 示例：通过 `acl.init()` → `acl.rt.set_device()` → `acl.rt.create_context()` 验证环境
- 无 NPU 时：`acl.init()` 返回非 0 错误码（`libascend_hal.so` 缺失）
- 替代验证方法：用 `atc --help` 验证工具链可用性

**耗时：** ~58s（06:57:23Z → 06:58:21Z）

---

### 操作 11：在容器内运行 AscendCL Hello World

**时间：** 06:58:21Z
**动作：** 启动容器，在容器内运行 AscendCL 初始化代码：

```bash
docker run -d --rm ascendai/cann:latest sleep 120
```

写入测试脚本 `/tmp/hello.py`：

```python
import sys, os
sys.path.insert(0, "/usr/local/Ascend/ascend-toolkit/latest/python/site-packages")

import acl

ret = acl.init()
print(f"[1] acl.init() ret={ret}")
if ret == 0:
    device_id = 0
    ret = acl.rt.set_device(device_id)
    context, ret = acl.rt.create_context(device_id)
    stream, ret = acl.rt.create_stream()
    print("Hello World from AscendCL!")
    acl.rt.destroy_stream(stream)
    acl.rt.destroy_context(context)
    acl.rt.reset_device(device_id)
    acl.finalize()
else:
    print("acl.init() failed - no NPU device")
```

运行：

```bash
docker exec <container> bash -c '
source /usr/local/Ascend/cann-9.0.0-beta.1/set_env.sh
export PYTHONPATH=/usr/local/Ascend/ascend-toolkit/latest/python/site-packages:$PYTHONPATH
python3 /tmp/hello.py
'
```

**输出：**
```
[1] acl.init() ret=500000
acl.init() failed - no NPU device
[Warning]: tiling struct [ReduceOpTilingDataV2] is conflict with one in file lp_norm_reduce.cc, line 41
```

**分析：** `acl.init()` 返回 `500000`（非零错误码），因为本机没有昇腾 NPU 硬件，`libascend_hal.so` 驱动库无法加载。AscendCL 运行时依赖物理 NPU 驱动，无法在纯 CPU 机器上初始化。

---

### 操作 12：改用 ATC 工具验证开发工具链

**时间：** 06:58:40Z
**动作：** ATC（AI Tensor Compiler）是模型转换工具，不依赖 NPU 硬件即可运行。

```bash
docker exec <container> bash -c '
source /usr/local/Ascend/cann-9.0.0-beta.1/set_env.sh
echo "atc path: $(which atc)"
atc --help 2>&1 | head -6
'
```

**输出：**
```
atc path: /usr/local/Ascend/cann-9.0.0-beta.1/bin/atc
ATC start working now, please wait for a moment.
usage: atc <args>
generate offline model example:
atc --model=./alexnet.prototxt --weight=./alexnet.caffemodel --framework=0 --output=./domi --soc_version=<soc_version>
generate offline model for single op example:
atc --singleop=./op_list.json --output=./op_model --soc_version=<soc_version>
```

**结果：** ✅ ATC 工具响应正常，CANN 开发工具链可用。
**耗时：** ~19s（06:57:23Z → 06:57:42Z，操作 10+12 合并约 57s）

---

### 使用阶段小结

| 步骤 | 操作 | 耗时 | 结果 |
|------|------|------|------|
| 操作 10 | 搜索 Hello World 示例 | ~58s | ✅ |
| 操作 11 | 运行 AscendCL acl.init() | ~19s | ❌（无 NPU，ret=500000） |
| 操作 12 | 运行 atc --help（替代验证） | ~19s | ✅ |
| **使用阶段总耗时** | | **~96s（约 1min 36s）** | ⚠️ |
| **状态** | | | ⚠️ warn（AscendCL 需要 NPU 硬件；ATC 工具链可用） |

---

## 四、贡献阶段

**开始时间：** 06:58:57Z

---

### 操作 13：找到 CANN 官方仓库地址

**时间：** 06:58:57Z
**动作：** 搜索 `gitcode.com ascend cann 仓库地址 URL`

**搜索结果：**
- CANN 主仓库：`https://gitcode.com/ascend/cann`
- Gitee 镜像：`https://gitee.com/ascend/cann`
- GitHub 镜像：`https://github.com/Ascend/cann`

**耗时：** ~17s

---

### 操作 14：用 Gitcode token 提交 Issue

**时间：** 06:59:14Z
**动作：** 查阅 API 文档，Gitcode 使用 v5 API（Gitee 风格），先确认 token 有效：

```bash
curl -s "https://api.gitcode.com/api/v5/user?access_token=<TOKEN>"
```

**输出：**
```json
{
  "login": "iamatest",
  "name": "iamatest",
  "id": "69c4d8600e37945d40c0380e",
  "html_url": "https://gitcode.com/iamatest"
}
```

Token 有效。继续提交 Issue：

```bash
curl -X POST "https://api.gitcode.com/api/v5/repos/ascend/cann/issues" \
  -H "Content-Type: application/json" \
  -H "private-token: <TOKEN>" \
  -d '{
    "title": "[TTFHW-TEST] Automated test issue 20260326T065914Z",
    "body": "This is an automated TTFHW test issue. Please ignore."
  }'
```

**输出：**
```json
{
  "error_code": 1003,
  "error_code_name": "NOT_EXIST",
  "error_message": "项目不存在",
  "trace_id": "6bbbbe5e63699625955204ea2bceee9e"
}
```

**HTTP 状态：** 404

**分析：** API 返回"项目不存在"。逐步排查：

| 尝试方式 | 请求 | 响应 |
|---------|------|------|
| v4 API + access_token in body | `POST /api/v4/projects/ascend%2Fcann/issues` | HTTP 405 |
| v5 API + access_token in body | `POST /api/v5/repos/ascend/cann/issues` | HTTP 404 "项目不存在" |
| v5 API + private-token header | `POST /api/v5/repos/ascend/cann/issues` | HTTP 404 "项目不存在" |
| v5 查询项目 | `GET /api/v5/repos/ascend/cann` | HTTP 400 "Project not found:ascend/cann" |

**根本原因：** `ascend/cann` 在 Gitcode 上对当前 token 用户（`iamatest`）不可见——可能该项目未公开、不存在于 Gitcode，或需要特定权限才能访问。Token 本身权限有限（`/api/v5/user/repos` 返回空列表，`read_projects` scope 403）。

**注：** Token 的 `user` 接口正常工作（HTTP 200），说明 Token 有效，是项目权限问题。

**耗时：** ~5min 38s（06:59:14Z → 07:04:35Z，包含多次 API 探测）

---

### 贡献阶段小结

| 步骤 | 操作 | 耗时 | 结果 |
|------|------|------|------|
| 操作 13 | 找到 CANN 仓库地址 | ~17s | ✅ |
| 操作 14 | 调用 Gitcode API 提交 Issue | ~5min 38s | ❌ |
| **贡献阶段总耗时** | | **~5min 55s** | ❌ |
| **状态** | | | ❌ fail（ascend/cann 项目在 Gitcode 上对当前用户不可见） |

**失败根因：** Gitcode 上 `ascend/cann` 项目对 `iamatest` 账号不可见（HTTP 404 "项目不存在"）。需要：
1. 确认项目在 Gitcode 上的实际路径（可能是 `Ascend/cann` 或其他命名空间）
2. 或者 token 需要配置 `read_projects` scope 才能查询项目列表进行验证

---

## 五、TTFHW 时间汇总

| 阶段 | 开始时间 | 结束时间 | 耗时 | 状态 |
|------|---------|---------|------|------|
| **了解** | 06:53:58Z | 06:55:19Z | **81s** | ⚠️ warn |
| **获取** | 06:55:19Z | 06:57:23Z | **124s** | ✅ pass |
| **使用** | 06:57:23Z | 06:58:57Z | **94s** | ⚠️ warn |
| **贡献** | 06:58:57Z | 07:04:35Z | **338s** | ❌ fail |
| **全流程总计** | 06:53:58Z | 07:04:35Z | **637s（约 10min 37s）** | — |

**TTFHW（Time To First Hello World）：**
从零开始到 CANN 容器可用（ATC 工具响应） ≈ **205s（约 3min 25s）**

> 注：含首次搜索文档（81s）+ Docker 环境就绪（124s）。如首次拉取镜像无缓存，获取阶段增加 ~6min，TTFHW ≈ **9min 25s**。

---

## 六、阻断点汇总

| 编号 | 阶段 | 阻断 | 影响 | 修复 |
|------|------|------|------|------|
| A1 | 了解 | 官方文档为 SPA，无法自动提取内容 | 需人工阅读浏览器 | 通过搜索摘要获取安装命令 |
| A2 | 获取 | `ascendhub.huawei.com` DNS 不可解析 | 官方镜像命令直接失败 | 改用 `ascendai/cann:latest`（Docker Hub） |
| A3 | 获取 | `zhongjun` 未激活 docker 组 | docker 命令全部 permission denied | `newgrp docker` |
| A4 | 使用 | 无 NPU 硬件，`acl.init()` 返回 500000 | AscendCL 运行时无法初始化 | 改用 `atc --help` 验证工具链 |
| A5 | 贡献 | Gitcode `ascend/cann` 对 token 用户不可见 | Issue 创建 HTTP 404 | 未解决（需确认项目路径或 token 权限） |

---

## 七、CANN 安装信息

| 属性 | 值 |
|------|-----|
| 镜像 | `ascendai/cann:latest`（Docker Hub 公开镜像） |
| 镜像 Digest | `sha256:a05cfa0b1c2232e1c9f631f0b65765746e0d0b5c8ea40d163f42aeecc853354b` |
| CANN 版本 | `9.0.0-beta.1` |
| innerversion | `V100R001C10B034` |
| 镜像大小 | `4,280,110,483 bytes（~4.08 GB）` |
| 镜像创建时间 | `2026-03-11T09:20:05Z` |
| 安装路径 | `/usr/local/Ascend/cann-9.0.0-beta.1/` |
| 核心工具 | `atc`、`ccec`、`aoe`、`bisheng`、`cannsim`、`asc_dumper` |
| 环境变量脚本 | `/usr/local/Ascend/cann-9.0.0-beta.1/set_env.sh` |
