# stages/stage_get_runpkg.py
import os
import subprocess
import tempfile
import requests
from stages.base import BaseStage
from metrics.collector import MetricsCollector


class GetRunPkgStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._tmp_file: str | None = None
        self._file_size_mb: float | None = None
        self._install_exit_code: int | None = None
        self._install_stderr: str = ""
        self._atc_available: bool | None = None

    def setup(self) -> None:
        pass

    def run(self) -> None:
        url = self._config.get("run_pkg_url", "")
        if not url:
            self._mc.add_error(
                phenomenon=".run 包下载 URL 未配置",
                severity="P1",
                cause="hiascend.com 为 SPA，URL 需手动更新到 config.yaml",
                solution="访问 hiascend.com 找到最新版本 .run 包下载链接，填入 run_pkg_url",
            )
            self._mc.set_fail()
            return

        timeout = self._config.get("timeout", {}).get("get_runpkg_s", 300)

        # 下载
        self._mc.start("download")
        try:
            resp = requests.get(url, stream=True, timeout=timeout)
            resp.raise_for_status()
            _, self._tmp_file = tempfile.mkstemp(suffix=".run")
            with open(self._tmp_file, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            self._mc.stop("download")
            self._file_size_mb = round(os.path.getsize(self._tmp_file) / (1024 * 1024), 1)
        except Exception as e:
            self._mc.stop("download")
            self._mc.add_error(
                phenomenon=f".run 包下载失败: {e}",
                severity="P0",
                cause="网络问题或 URL 失效",
                solution="检查 run_pkg_url 是否有效",
            )
            self._mc.set_fail()
            return

        # 安装
        os.chmod(self._tmp_file, 0o755)
        self._mc.start("install")
        try:
            result = subprocess.run(
                [self._tmp_file, "--install"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            self._mc.stop("install")
            self._install_exit_code = result.returncode
            self._install_stderr = result.stderr[:500]
            if result.returncode != 0:
                self._mc.add_error(
                    phenomenon=f".run 安装失败（exit code {result.returncode}）",
                    severity="P1",
                    cause="无 root 权限，或系统依赖缺失",
                    solution="使用 sudo 执行，或改用 Docker 方式安装",
                )
                self._mc.set_warn()
            else:
                # 安装成功，验证工具链
                r2 = subprocess.run(
                    ["bash", "-c", "source /usr/local/Ascend/cann-*/set_env.sh 2>/dev/null && atc --help"],
                    capture_output=True, text=True, timeout=30,
                )
                self._atc_available = (r2.returncode == 0)
        except subprocess.TimeoutExpired:
            self._mc.stop("install")
            self._mc.add_error(
                phenomenon="安装命令超时",
                severity="P1",
                cause="安装过程超时",
                solution="增大 timeout.get_runpkg_s 配置",
            )
            self._mc.set_warn()

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        if self._tmp_file and os.path.exists(self._tmp_file):
            try:
                os.remove(self._tmp_file)
            except Exception:
                pass

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "download_s": self._mc.elapsed("download"),
            "install_s": self._mc.elapsed("install"),
            "file_size_mb": self._file_size_mb,
            "install_exit_code": self._install_exit_code,
            "install_stderr": self._install_stderr,
            "atc_available": self._atc_available,
        })
        return d
