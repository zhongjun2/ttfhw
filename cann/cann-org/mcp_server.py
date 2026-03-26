import json
from mcp.server.fastmcp import FastMCP
from mcp import types
from runner import load_config, build_runner
from reports.reporter import Reporter

app = FastMCP("cann-ttfhw")
_last_report: dict | None = None
_config = load_config()


@app.tool()
async def cann_ttfhw_run_all() -> list[types.TextContent]:
    """Run all four TTFHW stages and return a full report."""
    global _last_report
    runner = build_runner(_config)
    _last_report = runner.run(["learn", "get", "use", "contribute"])
    reporter = Reporter(_last_report)
    return [types.TextContent(type="text", text=reporter.to_markdown())]


@app.tool()
async def cann_ttfhw_run_stage(
    stage: str,
    substage: str | None = None,
) -> list[types.TextContent]:
    """Run a single TTFHW stage. stage: learn|get|use|contribute. substage (contribute only): issue|pr_ci."""
    global _last_report
    runner = build_runner(_config)
    if stage == "contribute" and substage:
        from stages.stage_contribute import ContributeStage
        c = ContributeStage(_config)
        c.setup()
        if substage == "issue":
            c.run_issue()
        elif substage == "pr_ci":
            c.run_pr()
        result = {"stages": {"contribute": c.metrics()}}
    else:
        result = runner.run([stage])
    _last_report = result
    reporter = Reporter(result)
    return [types.TextContent(type="text", text=reporter.to_markdown())]


@app.tool()
async def cann_ttfhw_report(format: str = "markdown") -> list[types.TextContent]:
    """Return the latest TTFHW test report. format: json|markdown."""
    if _last_report is None:
        return [types.TextContent(type="text", text="No report available. Run cann_ttfhw_run_all first.")]
    reporter = Reporter(_last_report)
    if format == "json":
        return [types.TextContent(type="text", text=json.dumps(reporter.to_json(), indent=2, ensure_ascii=False))]
    return [types.TextContent(type="text", text=reporter.to_markdown())]


if __name__ == "__main__":
    import asyncio
    asyncio.run(app.run_stdio_async())
