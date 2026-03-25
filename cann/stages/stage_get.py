import docker
import time
from stages.base import BaseStage
from metrics.collector import MetricsCollector


class GetStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._client = None
        self._container = None
        self._image_size_mb: float | None = None
        self._setup_steps: int = 0

    def setup(self) -> None:
        self._client = docker.from_env()

    def run(self) -> None:
        image_name = self._config.get("cann_image", "")
        timeout = self._config.get("timeout", {}).get("get_s", 600)

        self._mc.start("wall_clock")
        self._mc.start("net_download")
        try:
            img = self._client.images.pull(image_name, timeout=timeout)
            self._mc.stop("net_download")
            self._image_size_mb = round(
                img.attrs.get("Size", 0) / (1024 * 1024), 1
            )
        except Exception as e:
            self._mc.stop("net_download")
            self._mc.add_error(f"docker_pull_error: {e}")
            self._mc.set_fail()
            self._mc.stop("wall_clock")
            return

        try:
            self._container = self._client.containers.run(
                image_name, detach=True, tty=True
            )
            self._setup_steps += 1
        except Exception as e:
            self._mc.add_error(f"container_start_failed: {e}")
            self._mc.set_fail()
            self._mc.stop("wall_clock")
            return

        result = self._container.exec_run("cann-info")
        self._setup_steps += 1
        if result.exit_code != 0:
            self._mc.add_error("cann_info_not_found")
            self._mc.set_fail()

        self._mc.stop("wall_clock")

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        if self._container:
            try:
                self._container.stop()
                self._container.remove()
            except Exception:
                pass

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        wall = self._mc.elapsed("wall_clock")
        net = self._mc.elapsed("net_download")
        d.update({
            "wall_clock_s": wall,
            "net_download_s": net,
            "image_size_mb": self._image_size_mb,
            "setup_steps": self._setup_steps,
        })
        return d
