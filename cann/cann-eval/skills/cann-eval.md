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
