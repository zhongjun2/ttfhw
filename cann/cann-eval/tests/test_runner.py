# tests/test_runner.py
from unittest.mock import MagicMock, patch
from runner import Runner, get_stage_names


def _make_pass_stage():
    stage = MagicMock()
    stage.verify.return_value = True
    stage.metrics.return_value = {"status": "pass", "breakpoints": []}
    stage._mc = MagicMock()
    stage._container = None
    return stage


def _make_fail_stage():
    stage = MagicMock()
    stage.verify.return_value = False
    stage.metrics.return_value = {"status": "fail", "breakpoints": [{"severity": "P0", "phenomenon": "test error", "cause": "", "solution": ""}]}
    stage._mc = MagicMock()
    stage._container = None
    return stage


def test_runner_runs_all_stages():
    stages = {
        "learn": _make_pass_stage(),
        "get_docker": _make_pass_stage(),
        "get_runpkg": _make_pass_stage(),
        "use_quickstart": _make_pass_stage(),
        "use_qwen2": _make_pass_stage(),
    }
    config = {"on_stage_failure": "continue"}
    runner = Runner(stages, config)
    report = runner.run(["learn", "get_docker", "use_quickstart"])
    assert "learn" in report["stages"]
    assert "get_docker" in report["stages"]
    assert "use_quickstart" in report["stages"]
    assert "get_runpkg" not in report["stages"]


def test_runner_injects_container_into_use_quickstart():
    mock_container = MagicMock()
    get_docker = _make_pass_stage()
    get_docker._container = mock_container
    use_qs = _make_pass_stage()
    use_qs._container = None
    stages = {
        "learn": _make_pass_stage(),
        "get_docker": get_docker,
        "get_runpkg": _make_pass_stage(),
        "use_quickstart": use_qs,
        "use_qwen2": _make_pass_stage(),
    }
    config = {"on_stage_failure": "continue"}
    runner = Runner(stages, config)
    runner.run(["get_docker", "use_quickstart"])
    assert use_qs._container is mock_container


def test_runner_abort_on_failure():
    stages = {
        "learn": _make_fail_stage(),
        "get_docker": _make_pass_stage(),
        "get_runpkg": _make_pass_stage(),
        "use_quickstart": _make_pass_stage(),
        "use_qwen2": _make_pass_stage(),
    }
    config = {"on_stage_failure": "abort"}
    runner = Runner(stages, config)
    report = runner.run(Runner.STAGE_ORDER)
    # 因为 learn 失败且 abort，后续 stage 不应执行
    assert "learn" in report["stages"]
    assert "get_docker" not in report["stages"]


def test_runner_continue_on_failure():
    stages = {
        "learn": _make_fail_stage(),
        "get_docker": _make_pass_stage(),
        "get_runpkg": _make_pass_stage(),
        "use_quickstart": _make_pass_stage(),
        "use_qwen2": _make_pass_stage(),
    }
    config = {"on_stage_failure": "continue"}
    runner = Runner(stages, config)
    report = runner.run(Runner.STAGE_ORDER)
    # continue 模式下，所有 stage 都应执行
    assert "learn" in report["stages"]
    assert "get_docker" in report["stages"]


def test_get_stage_names_docker():
    assert get_stage_names("docker", None) == ["learn", "get_docker", "use_quickstart", "use_qwen2"]


def test_get_stage_names_single_stage():
    assert get_stage_names("both", "learn") == ["learn"]
