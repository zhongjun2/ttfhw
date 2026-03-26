# runner.py
import datetime
import json
import os
import platform
import subprocess
import sys
import yaml
from stages.base import BaseStage
from stages.stage_learn import LearnStage
from stages.stage_get_docker import GetDockerStage
from stages.stage_get_runpkg import GetRunPkgStage
from stages.stage_use_quickstart import UseQuickStartStage
from stages.stage_use_qwen2 import UseQwen2Stage
from reports.reporter import Reporter


class Runner:
    STAGE_ORDER = ["learn", "get_docker", "get_runpkg", "use_quickstart", "use_qwen2"]

    def __init__(self, stages: dict[str, BaseStage], config: dict):
        self._stages = stages
        self._config = config

    def run(self, stage_names: list[str]) -> dict:
        report = {
            "test_date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "mode": "auto",
            "environment": _get_environment(),
            "stages": {},
            "breakpoints": [],
        }
        on_failure = self._config.get("on_stage_failure", "continue")
        get_docker_stage: GetDockerStage | None = None
        deferred_teardown = []

        for name in self.STAGE_ORDER:
            if name not in stage_names:
                continue
            stage = self._stages[name]

            # 注入容器句柄
            if name == "use_quickstart" and get_docker_stage and get_docker_stage._container:
                stage._container = get_docker_stage._container

            try:
                stage.setup()
                stage.run()
                ok = stage.verify()
            except Exception as e:
                ok = False
                stage._mc.add_error(
                    phenomenon=f"Stage 异常: {e}",
                    severity="P0",
                    cause="未捕获的异常",
                    solution="查看完整 traceback",
                )
                stage._mc.set_fail()

            # get_docker 延迟 teardown（等 use_quickstart 完成后再清理容器）
            if name == "get_docker" and "use_quickstart" in stage_names:
                get_docker_stage = stage
                deferred_teardown.append(stage)
            else:
                try:
                    stage.teardown()
                except Exception:
                    pass

            # use_quickstart 完成后，清理 get_docker 容器
            if name == "use_quickstart":
                for s in deferred_teardown:
                    try:
                        s.teardown()
                    except Exception:
                        pass
                deferred_teardown.clear()

            metrics_data = stage.metrics()
            report["stages"][name] = metrics_data
            # 汇总断点到顶层
            for bp in metrics_data.get("breakpoints", []):
                report["breakpoints"].append({"stage": name, **bp})

            if not ok and on_failure == "abort":
                break

        # 清理剩余延迟 teardown
        for s in deferred_teardown:
            try:
                s.teardown()
            except Exception:
                pass

        return report


def _get_environment() -> dict:
    try:
        docker_ver = subprocess.check_output(
            ["docker", "--version"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        docker_ver = "unknown"
    return {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "python": platform.python_version(),
        "docker_version": docker_ver,
    }


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_runner(config: dict) -> Runner:
    stages: dict[str, BaseStage] = {
        "learn": LearnStage(config),
        "get_docker": GetDockerStage(config),
        "get_runpkg": GetRunPkgStage(config),
        "use_quickstart": UseQuickStartStage(config),
        "use_qwen2": UseQwen2Stage(config),
    }
    return Runner(stages=stages, config=config)


def get_stage_names(install: str, stage: str | None) -> list[str]:
    if stage:
        return [stage]
    if install == "docker":
        return ["learn", "get_docker", "use_quickstart", "use_qwen2"]
    elif install == "run_pkg":
        return ["learn", "get_runpkg", "use_qwen2"]
    else:  # both
        return Runner.STAGE_ORDER


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CANN 易用性评估工具")
    parser.add_argument("--mode", choices=["auto", "manual"], default="auto")
    parser.add_argument("--install", choices=["docker", "run_pkg", "both"], default="both")
    parser.add_argument("--stage", choices=["learn", "get_docker", "get_runpkg", "use_quickstart", "use_qwen2"])
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--output", help="输出文件路径（默认打印到 stdout）")
    args = parser.parse_args()

    if args.mode == "manual":
        import manual.recorder as rec
        rec.main()
        sys.exit(0)

    config = load_config(args.config)
    runner = build_runner(config)
    stage_names = get_stage_names(args.install, args.stage)
    report = runner.run(stage_names)
    reporter = Reporter(report)

    if args.format == "json":
        output = json.dumps(reporter.to_json(), indent=2, ensure_ascii=False)
    else:
        output = reporter.to_markdown()

    if args.output:
        dirname = os.path.dirname(args.output)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        with open(args.output, "w") as f:
            f.write(output)
        print(f"报告已写入 {args.output}")
    else:
        print(output)
