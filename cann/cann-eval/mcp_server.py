# mcp_server.py
import json
import os
from mcp.server.fastmcp import FastMCP
from runner import load_config, build_runner, get_stage_names, Runner
from reports.reporter import Reporter

mcp = FastMCP("cann-eval")
_last_report: dict | None = None


@mcp.tool()
def cann_eval_run_all(install_mode: str = "both") -> str:
    """
    运行 CANN 易用性评估全部阶段。
    install_mode: "docker" | "run_pkg" | "both"（默认 both）
    返回中文 Markdown 报告。
    """
    global _last_report
    config = load_config()
    runner = build_runner(config)
    stage_names = get_stage_names(install_mode, None)
    _last_report = runner.run(stage_names)
    return Reporter(_last_report).to_markdown()


@mcp.tool()
def cann_eval_run_stage(stage_name: str) -> str:
    """
    运行单个阶段。
    stage_name: "learn" | "get_docker" | "get_runpkg" | "use_quickstart" | "use_qwen2"
    返回该阶段的 JSON 指标。
    """
    global _last_report
    config = load_config()
    runner = build_runner(config)
    result = runner.run([stage_name])
    _last_report = result
    return json.dumps(result["stages"].get(stage_name, {}), ensure_ascii=False, indent=2)


@mcp.tool()
def cann_eval_report(format: str = "markdown") -> str:
    """
    获取最新一次评估报告。
    format: "markdown"（默认）| "json"
    如果还没有运行过评估，返回提示信息。
    """
    if _last_report is None:
        return "尚未运行评估。请先调用 cann_eval_run_all。"
    reporter = Reporter(_last_report)
    if format == "json":
        return json.dumps(reporter.to_json(), ensure_ascii=False, indent=2)
    return reporter.to_markdown()


if __name__ == "__main__":
    mcp.run()
