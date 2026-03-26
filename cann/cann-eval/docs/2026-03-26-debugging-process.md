# CANN 评估工具调试过程记录

**日期：** 2026-03-26
**作者：** Claude Code（AI 辅助评估）

---

## 背景

评估工具按设计规格实现后，在实际运行中遇到多个工程问题。本文记录每个问题的发现过程、根本原因和修复方案，以便后续维护和参考。

---

## 问题 1：Docker `images.pull()` 不支持 `timeout` 参数

**发现时间：** 2026-03-26 上午
**阶段：** `get_docker`

**现象：**
```
TypeError: DockerClient.images.pull() got an unexpected keyword argument 'timeout'
```

**根本原因：**
docker Python SDK v7+ 的 `images.pull()` 不接受 `timeout` 关键字参数，该参数在旧版本中存在。

**修复：**
```python
# 修改前
img = self._client.images.pull(image_name, timeout=timeout)
# 修改后
img = self._client.images.pull(image_name)
```

---

## 问题 2：容器启动后立即退出（exec_run 失败）

**发现时间：** 2026-03-26 上午
**阶段：** `get_docker`

**现象：**
`containers.run()` 启动容器后，`exec_run("atc --help")` 报容器不存在或退出错误。

**根本原因：**
容器没有指定前台进程，启动后立即退出。`exec_run` 在已退出的容器上无法执行命令。

**修复：**
```python
# 修改前
self._container = self._client.containers.run(image_name, detach=True, tty=True)
# 修改后
self._container = self._client.containers.run(
    image_name, command="tail -f /dev/null", detach=True, tty=True
)
```

---

## 问题 3：pip 安装 torch + torch-npu 依赖冲突（ResolutionImpossible）

**发现时间：** 2026-03-26 上午
**阶段：** `use_qwen2`

**现象：**
```
pip._internal.exceptions.DistributionNotFound: The 'torch-npu' distribution requires 'torch==2.1.0'
ResolutionImpossible
```

**根本原因：**
torch-npu 指定了精确的 torch 版本依赖（如 `torch==2.1.0`），与新版 torch 冲突。在 Python 3.12 环境下，torch-npu 的依赖约束导致解析失败。

**修复（分两步安装）：**
1. 先安装 `torch + modelscope + transformers + accelerate`（基础依赖，无冲突）
2. 模型下载完成后，再用 `--no-deps` 安装 `torch-npu`（跳过依赖校验）

```python
# 基础依赖先装
install_steps_pre = [["torch", "modelscope", "transformers", "accelerate"]]
# 模型下载完成后
subprocess.run([python, "-m", "pip", "install", "-q", "torch-npu", "--no-deps"], ...)
```

---

## 问题 4：torch-npu 安装顺序导致 modelscope CLI 崩溃

**发现时间：** 2026-03-26 13:03（第1次运行）
**阶段：** `use_qwen2`（模型下载步骤）
**耗时：** install_s=535s，download_s=3s（下载即失败）

**现象：**
`modelscope download` 命令崩溃，报 `ImportError: libhccl.so: cannot open shared object file`

**根本原因：**
`torch_npu/__init__.py` 在 import 时会自动尝试 `import torch_npu.npu`，而 `torch_npu.npu` 依赖 `libhccl.so`（CANN 运行时库），在无 NPU 机器上不存在。
由于 modelscope 的 CLI 脚本会导入 torch，torch 又通过 entrypoint 机制加载 torch_npu，因此只要 torch-npu 已安装，modelscope 命令就无法启动。

**修复：**
将 torch-npu 的安装移到**模型下载完成之后**，确保 modelscope 在无 torch-npu 的环境中运行。

---

## 问题 5：torch 通过 entrypoint 自动加载 torch_npu 后端

**发现时间：** 2026-03-26 13:14—13:55（第2~4次运行）
**阶段：** `use_qwen2`（推理步骤）

**现象：**
推理脚本中虽然用 try/except 捕获了 `import torch_npu`，但推理仍然崩溃：
```
RuntimeError: Failed to load the backend extension: torch_npu.
You can disable extension auto-loading with TORCH_DEVICE_BACKEND_AUTOLOAD=0
```

**根本原因（多层）：**

torch-npu 安装时向 Python 包元数据（`entry_points`）注册了一个 torch 后端插件。
当 `import torch` 执行时，`torch/__init__.py` 调用 `_import_device_backends()`，通过 `importlib.metadata` 查找所有注册的后端并自动加载，这完全绕过了 `sys.modules` 中的占位符。

**修复过程（三次迭代）：**

**第1次修复（不足）：** 只加 try/except
```python
try:
    import torch_npu
except Exception:
    pass
```
→ 还是崩溃，因为 torch 的 `_import_device_backends()` 另走 entrypoint 路径

**第2次修复（不足）：** 注入 dummy module 到 sys.modules
```python
except Exception:
    _dummy = types.ModuleType('torch_npu')
    sys.modules['torch_npu'] = _dummy
```
→ 部分有效，但 transformers 调用 `importlib.util.find_spec('torch_npu')` 时报：
```
ValueError: torch_npu.__spec__ is None
```

**第3次修复（最终方案）：** 设置 `TORCH_DEVICE_BACKEND_AUTOLOAD=0` + 给 dummy module 设置合法 `__spec__`
```python
os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'   # 禁止 torch 自动加载 NPU 后端
try:
    import torch_npu
except Exception:
    _dummy = types.ModuleType('torch_npu')
    _dummy.__spec__ = importlib.machinery.ModuleSpec('torch_npu', loader=None)
    sys.modules['torch_npu'] = _dummy
    sys.modules['torch_npu.npu'] = types.ModuleType('torch_npu.npu')
```

---

## 问题 6：`device_map='cpu'` 需要 accelerate 包

**发现时间：** 2026-03-26 14:00（第5次运行前）
**阶段：** `use_qwen2`（推理步骤）

**现象：**
```
ValueError: Using a `device_map` ... requires `accelerate`.
You can install it with `pip install accelerate`
```

**根本原因：**
transformers 5.x 将 `device_map` 参数的处理移到了 `accelerate` 包中，不再内置。安装依赖列表中未包含 `accelerate`。

**修复：**
```python
install_steps_pre = [["torch", "modelscope", "transformers", "accelerate"]]
```

---

## 问题 7：Google 搜索未返回 hiascend.com（SEO 断点）

**发现时间：** 2026-03-26 首次运行
**阶段：** `learn`

**现象：**
搜索 `"CANN 昇腾 安装"` 的前10条结果中，没有任何 `hiascend.com` 链接。

**性质：** 这不是代码 bug，而是真实的用户体验断点（P1）：新用户通过 Google 搜索 CANN，找不到官方文档。
**影响：** 新用户可能通过第三方博客或过时教程学习 CANN，增加踩坑概率。

---

## 各次运行时间汇总

| 运行次序 | 时间 | install_s | download_s | inference_s | 结果 | 失败原因 |
|---------|------|-----------|-----------|-------------|------|---------|
| 第1次 | 13:03 | 535s | 3s | — | ❌ | torch-npu 导致 modelscope CLI 崩溃，下载未启动 |
| 第2次 | 13:14 | 88s | **2012s（首次下载）** | 3s | ❌ | torch entrypoint 加载 torch_npu 崩溃 |
| 第3次 | 13:50 | 86s | 9s（缓存） | 4s | ❌ | dummy `__spec__` 为 None，find_spec 报 ValueError |
| 第4次 | 13:55 | 84s | 7s（缓存） | 4s | ❌ | 缺 accelerate 包 |
| 第5次 | 14:03 | 83s | 6s（缓存） | 6s | ✅ | — |

**Qwen2 阶段累计实际消耗：** ≈ 2939s（约 49 分钟）

---

## 结论

Qwen2-0.5B 在无 NPU 机器上的 CPU 推理**技术上可行**，但有以下已知工程问题：

1. **torch-npu 与 CPU 的兼容性极差**：安装后会干扰 torch 导入链，需要多个 workaround（`TORCH_DEVICE_BACKEND_AUTOLOAD=0` + dummy module + `--no-deps` 安装顺序）
2. **首次模型下载耗时长**：Qwen2-0.5B（953 MB）通过 ModelScope 下载约 33 分钟（受网络速度影响）
3. **pip 安装不稳定**：首次运行 pip 耗时 535s（含超时重试），后续缓存后约 83s

这些问题真实反映了 CANN 在 CPU 开发机上的用户体验挑战。
