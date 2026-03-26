# metrics/collector.py
import time


class MetricsCollector:
    def __init__(self):
        self._starts: dict[str, float] = {}
        self._stops: dict[str, float] = {}
        self._breakpoints: list[dict] = []
        self._warn = False
        self._fail = False

    def start(self, name: str) -> None:
        self._starts[name] = time.monotonic()

    def stop(self, name: str) -> None:
        self._stops[name] = time.monotonic()

    def elapsed(self, name: str) -> float | None:
        if name not in self._starts or name not in self._stops:
            return None
        return round(self._stops[name] - self._starts[name], 3)

    def add_error(
        self,
        phenomenon: str,
        severity: str = "P1",
        cause: str = "",
        solution: str = "",
    ) -> None:
        self._breakpoints.append({
            "severity": severity,
            "phenomenon": phenomenon,
            "cause": cause,
            "solution": solution,
        })

    def set_warn(self) -> None:
        self._warn = True

    def set_fail(self) -> None:
        self._fail = True

    def status(self) -> str:
        if self._fail:
            return "fail"
        if self._warn:
            return "warn"
        return "pass"

    def to_dict(self) -> dict:
        result: dict = {"status": self.status(), "breakpoints": self._breakpoints}
        for name in self._stops:
            result[f"{name}_s"] = self.elapsed(name)
        return result
