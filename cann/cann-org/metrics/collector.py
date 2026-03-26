import time


class MetricsCollector:
    def __init__(self):
        self._starts: dict[str, float] = {}
        self._stops: dict[str, float] = {}
        self.errors: list[str] = []
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

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

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
        result = {"status": self.status(), "errors": self.errors}
        for name in self._stops:
            result[f"{name}_s"] = self.elapsed(name)
        return result
