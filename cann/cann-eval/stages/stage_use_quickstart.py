# stages/stage_use_quickstart.py
from stages.base import BaseStage
from metrics.collector import MetricsCollector


class UseQuickStartStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._container = None  # 由 Runner 注入
        self._atc_exit_code: int | None = None
        self._atc_help_output: str = ""
        self._set_env_found: bool = False

    def setup(self) -> None:
        if self._container is None:
            self._mc.add_error(
                phenomenon="容器句柄未注入",
                severity="P0",
                cause="GetDockerStage 未成功完成，或 Runner 未注入容器",
                solution="确保 GetDockerStage 先于 UseQuickStartStage 运行",
            )
            self._mc.set_fail()

    def run(self) -> None:
        if self._container is None:
            return
        self._mc.start("toolchain")
        try:
            result = self._container.exec_run(
                "bash -c 'source /usr/local/Ascend/cann-*/set_env.sh 2>/dev/null && which atc && atc --help 2>&1 | head -5'"
            )
            self._mc.stop("toolchain")
            self._atc_exit_code = result.exit_code
            raw = result.output
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="ignore")
            self._atc_help_output = raw[:200]
            self._set_env_found = (result.exit_code == 0)

            if result.exit_code != 0:
                self._mc.add_error(
                    phenomenon=f"atc --help 返回退出码 {result.exit_code}",
                    severity="P1",
                    cause="CANN 工具链未正确安装",
                    solution="检查容器内 /usr/local/Ascend/ 目录",
                )
                self._mc.set_warn()
        except Exception as e:
            self._mc.stop("toolchain")
            self._mc.add_error(
                phenomenon=f"容器命令执行失败: {e}",
                severity="P0",
                cause="容器已退出或网络问题",
                solution="重新运行 GetDockerStage",
            )
            self._mc.set_fail()

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        # 容器清理由 Runner 触发 GetDockerStage.teardown()
        pass

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "toolchain_s": self._mc.elapsed("toolchain"),
            "set_env_found": self._set_env_found,
            "atc_exit_code": self._atc_exit_code,
            "atc_help_output": self._atc_help_output,
        })
        return d
