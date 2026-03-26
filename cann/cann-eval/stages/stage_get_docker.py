# stages/stage_get_docker.py
import docker
from stages.base import BaseStage
from metrics.collector import MetricsCollector


class GetDockerStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._client = None
        self._container = None
        self._image_size_mb: float | None = None
        self._cann_version: str | None = None
        self._atc_available: bool = False

    def setup(self) -> None:
        try:
            self._client = docker.from_env()
        except Exception as e:
            self._mc.add_error(
                phenomenon=f"Docker 客户端初始化失败: {e}",
                severity="P0",
                cause="Docker 未安装或当前用户无权限",
                solution="安装 Docker 并将用户加入 docker 组（newgrp docker）",
            )
            self._mc.set_fail()

    def run(self) -> None:
        if self._client is None:
            return
        image_name = self._config.get("cann_image", "ascendai/cann:latest")
        timeout = self._config.get("timeout", {}).get("get_docker_s", 600)

        self._mc.start("wall_clock")
        self._mc.start("net_download")
        try:
            img = self._client.images.pull(image_name)
            self._mc.stop("net_download")
            self._image_size_mb = round(img.attrs.get("Size", 0) / (1024 * 1024), 1)
        except Exception as e:
            self._mc.stop("net_download")
            self._mc.add_error(
                phenomenon=f"docker pull 失败: {e}",
                severity="P0",
                cause="镜像地址不可达或网络超时",
                solution="确认使用 ascendai/cann:latest（Docker Hub 公开镜像）",
            )
            self._mc.set_fail()
            self._mc.stop("wall_clock")
            return

        try:
            self._container = self._client.containers.run(
                image_name, command="tail -f /dev/null", detach=True, tty=True
            )
        except Exception as e:
            self._mc.add_error(
                phenomenon=f"容器启动失败: {e}",
                severity="P0",
                cause="Docker 资源不足或镜像损坏",
                solution="检查磁盘空间和内存",
            )
            self._mc.set_fail()
            self._mc.stop("wall_clock")
            return

        # 验证 CANN 工具链
        result = self._container.exec_run(
            "bash -c 'source /usr/local/Ascend/cann-*/set_env.sh 2>/dev/null && atc --help 2>&1 | head -3'"
        )
        if result.exit_code == 0:
            self._atc_available = True
        else:
            self._mc.add_error(
                phenomenon="atc --help 返回非零退出码",
                severity="P1",
                cause="CANN 工具链未正确安装或 set_env.sh 路径变更",
                solution="手动检查容器内 /usr/local/Ascend/ 目录结构",
            )
            self._mc.set_warn()

        # 读取 CANN 版本
        ver_result = self._container.exec_run(
            "bash -c \"cat /usr/local/Ascend/cann-*/x86_64-linux/ascend_toolkit_install.info 2>/dev/null | grep version | head -1\""
        )
        if ver_result.exit_code == 0:
            self._cann_version = ver_result.output.decode("utf-8", errors="ignore").strip()

        self._mc.stop("wall_clock")

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        # Runner 负责决定何时调用（需等 UseQuickStartStage 完成后）
        if self._container:
            try:
                self._container.stop(timeout=5)
                self._container.remove()
            except Exception:
                pass
            self._container = None

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "net_download_s": self._mc.elapsed("net_download"),
            "wall_clock_s": self._mc.elapsed("wall_clock"),
            "image_size_mb": self._image_size_mb,
            "cann_version": self._cann_version,
            "atc_available": self._atc_available,
        })
        return d
