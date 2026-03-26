# reports/reporter.py
import json


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
| .run 包 | {grp.get('download_s', '?')}s (下载) | {len(grp.get('breakpoints', []))} | {'✅' if grp.get('atc_available') is True else ('❌' if grp.get('atc_available') is False else '—')} |

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
