import datetime
import sys
import json
import os
import yaml
from stages.base import BaseStage
from stages.stage_learn import LearnStage
from stages.stage_get import GetStage
from stages.stage_use import UseStage
from stages.stage_contribute import ContributeStage
from reports.reporter import Reporter


class Runner:
    COMMUNITY = "cann"
    SCENARIO = "zero-to-custom-op"

    def __init__(self, stages: dict[str, BaseStage], config: dict):
        self._stages = stages
        self._config = config

    def run(self, stage_names: list[str]) -> dict:
        report = {
            "community": self.COMMUNITY,
            "scenario": self.SCENARIO,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "cann_version": self._config.get("cann_image", "unknown").split(":")[-1],
            "stages": {},
        }
        abort_on_failure = self._config.get("on_stage_failure", "continue") == "abort"
        completed: dict[str, object] = {}
        deferred_teardown: list = []

        for name in stage_names:
            stage = self._stages.get(name)
            if stage is None:
                continue
            # Wire container from GetStage into UseStage before running Use
            if name == "use" and "get" in completed:
                stage._container = completed["get"]._container
            try:
                stage.setup()
                stage.run()
                ok = stage.verify()
            except Exception:
                ok = False
            # Defer GetStage teardown until after UseStage completes
            if name == "get" and "use" in stage_names:
                deferred_teardown.append(stage)
            else:
                try:
                    stage.teardown()
                except Exception:
                    pass
                # Also flush any deferred teardowns after use stage
                if name == "use":
                    for deferred in deferred_teardown:
                        try:
                            deferred.teardown()
                        except Exception:
                            pass
                    deferred_teardown.clear()
            completed[name] = stage
            report["stages"][name] = stage.metrics()
            if not ok and abort_on_failure:
                # Flush deferred teardowns before aborting
                for deferred in deferred_teardown:
                    try:
                        deferred.teardown()
                    except Exception:
                        pass
                break

        # Flush any remaining deferred teardowns
        for deferred in deferred_teardown:
            try:
                deferred.teardown()
            except Exception:
                pass

        return report


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        raw = yaml.safe_load(f)
    # Expand environment variables in token fields
    for key in ("gitcode_token",):
        val = raw.get(key, "")
        if isinstance(val, str) and val.startswith("${") and val.endswith("}"):
            env_var = val[2:-1]
            raw[key] = os.environ.get(env_var, "")
    # Expand search.bing_api_key
    search = raw.get("search", {})
    api_key = search.get("bing_api_key", "")
    if isinstance(api_key, str) and api_key.startswith("${") and api_key.endswith("}"):
        env_var = api_key[2:-1]
        search["bing_api_key"] = os.environ.get(env_var, "")
    return raw


def build_runner(config: dict) -> "Runner":
    stages = {
        "learn": LearnStage(config),
        "get": GetStage(config),
        "use": UseStage(config),
        "contribute": ContributeStage(config),
    }
    return Runner(stages=stages, config=config)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CANN TTFHW Test Runner")
    parser.add_argument("--stages", nargs="*",
                        default=["learn", "get", "use", "contribute"],
                        help="Stages to run")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    runner = build_runner(config)
    report = runner.run(args.stages)
    reporter = Reporter(report)

    if args.format == "json":
        print(json.dumps(reporter.to_json(), indent=2, ensure_ascii=False))
    else:
        print(reporter.to_markdown())
