import json


class Reporter:
    def __init__(self, data: dict):
        self._data = data

    def to_json(self) -> dict:
        return self._data

    def to_markdown(self) -> str:
        d = self._data
        stages = d.get("stages", {})
        learn = stages.get("learn", {})
        get = stages.get("get", {})
        use = stages.get("use", {})
        issue = stages.get("contribute", {}).get("issue", {})
        pr_ci = stages.get("contribute", {}).get("pr_ci", {})

        def icon(s): return "✅" if s == "pass" else ("⚠️" if s == "warn" else "❌")

        rows = [
            f"| 了解 | {icon(learn.get('status',''))} {learn.get('status','')} "
            f"| 搜索 {learn.get('search_s','?')}s，导航 {learn.get('nav_hops','?')} 跳 "
            f"| 官方链接排名第{learn.get('official_link_rank','?')} |",
            f"| 获取 | {icon(get.get('status',''))} {get.get('status','')} "
            f"| 总计 {get.get('wall_clock_s','?')}s，下载 {get.get('net_download_s','?')}s "
            f"| 镜像 {get.get('image_size_mb','?')}MB |",
            f"| 使用 | {icon(use.get('status',''))} {use.get('status','')} "
            f"| 编译 {use.get('compile_s','?')}s，运行 {use.get('run_s','?')}s | 无报错 |",
            f"| 贡献-Issue | {icon(issue.get('status',''))} {issue.get('status','')} "
            f"| 提交 {issue.get('submit_s','?')}s，首次响应 {issue.get('first_response_s','?')}s | — |",
            f"| 贡献-PR CI | {icon(pr_ci.get('status',''))} {pr_ci.get('status','')} "
            f"| 排队 {pr_ci.get('ci_queue_s','?')}s，准备 {pr_ci.get('ci_prepare_s','?')}s，"
            f"运行 {pr_ci.get('ci_run_s','?')}s | CI结果: {pr_ci.get('ci_result','?')} |",
        ]

        all_errors = []
        for stage_name, stage_data in stages.items():
            if isinstance(stage_data, dict):
                for err in stage_data.get("errors", []):
                    all_errors.append(f"- [{stage_name}] {err}")
                for sub in stage_data.values():
                    if isinstance(sub, dict):
                        for err in sub.get("errors", []):
                            all_errors.append(f"- [{stage_name}] {err}")

        anomalies = "\n".join(all_errors) if all_errors else "（无）"

        return f"""# CANN TTFHW 测试报告

**时间：** {d.get('timestamp', '')}
**CANN 版本：** {d.get('cann_version', '')}
**场景：** {d.get('scenario', '')}

## 各阶段耗时汇总

| 阶段 | 状态 | 关键时间 | 备注 |
|------|------|---------|------|
{chr(10).join(rows)}

## 异常记录

{anomalies}
"""
