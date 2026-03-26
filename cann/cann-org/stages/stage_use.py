import os
import tarfile
import io
from stages.base import BaseStage
from metrics.collector import MetricsCollector

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures", "custom_op")
EXPECTED_OUTPUT = [11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0]
TOLERANCE = 1e-5


class UseStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._container = None
        self._compile_errors = 0
        self._compile_warnings = 0
        self._run_errors = 0

    def setup(self) -> None:
        pass  # Container injected by runner from GetStage

    def run(self) -> None:
        if self._container is None:
            self._mc.add_error("container_not_available")
            self._mc.set_fail()
            return
        self._copy_fixtures()

        self._mc.start("compile")
        result = self._container.exec_run("bash /op/build.sh", workdir="/op")
        self._mc.stop("compile")

        output = result.output.decode("utf-8", errors="replace")
        if result.exit_code != 0 or "BUILD_SUCCESS" not in output:
            self._compile_errors = output.lower().count("error:")
            self._mc.add_error("compile_failed")
            self._mc.set_fail()
            return
        self._compile_warnings = output.lower().count("warning:")

        self._mc.start("run")
        run_result = self._container.exec_run("python run.py", workdir="/op")
        self._mc.stop("run")

        if run_result.exit_code != 0:
            self._run_errors += 1
            self._mc.add_error("run_failed")
            self._mc.set_fail()
            return

        self._verify_output(run_result.output.decode().strip())

    def _copy_fixtures(self) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            tar.add(FIXTURE_DIR, arcname="op")
        buf.seek(0)
        self._container.put_archive("/", buf)

    def _verify_output(self, raw: str) -> None:
        try:
            values = [float(v) for v in raw.split(",")]
            if len(values) != len(EXPECTED_OUTPUT):
                self._mc.add_error(f"output_length_mismatch: got {len(values)}, want {len(EXPECTED_OUTPUT)}")
                self._mc.set_fail()
                return
            for got, want in zip(values, EXPECTED_OUTPUT):
                if abs(got - want) >= TOLERANCE:
                    self._mc.add_error(f"output_mismatch: got {got}, want {want}")
                    self._mc.set_fail()
                    return
        except Exception as e:
            self._mc.add_error(f"output_parse_error: {e}")
            self._mc.set_fail()

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        pass

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "compile_s": self._mc.elapsed("compile"),
            "run_s": self._mc.elapsed("run"),
            "compile_errors": self._compile_errors,
            "compile_warnings": self._compile_warnings,
            "run_errors": self._run_errors,
        })
        return d
