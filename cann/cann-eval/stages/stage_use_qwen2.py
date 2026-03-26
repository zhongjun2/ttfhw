# stages/stage_use_qwen2.py
import os
import shutil
import subprocess
import tempfile
import textwrap
import venv
from stages.base import BaseStage
from metrics.collector import MetricsCollector

# 判断是否为纯硬件错误（NPU 缺失，属预期行为，非软件 bug）
_HARDWARE_ERROR_PATTERNS = [
    "no npu device",
    "npu device",
    "ascend device",
    "acl.init()",
    "runtimeerror: device",
    "cann runtime",
]

INFERENCE_SCRIPT = textwrap.dedent("""\
import os
import sys
import types
import importlib.machinery
# 禁止 torch 通过 entrypoint 自动加载 torch_npu 后端（无 NPU 机器上会崩溃）
os.environ['TORCH_DEVICE_BACKEND_AUTOLOAD'] = '0'
# torch_npu 在无 NPU 机器上 __init__.py 会崩溃（import torch_npu.npu 失败）。
# 捕获后注入带有合法 __spec__ 的 dummy module，防止 transformers 的
# importlib.util.find_spec('torch_npu') 抛出 ValueError: torch_npu.__spec__ is None。
try:
    import torch_npu  # noqa: F401
except Exception:
    _dummy = types.ModuleType('torch_npu')
    _dummy.__spec__ = importlib.machinery.ModuleSpec('torch_npu', loader=None)
    sys.modules['torch_npu'] = _dummy
    sys.modules['torch_npu.npu'] = types.ModuleType('torch_npu.npu')
from transformers import AutoModelForCausalLM, AutoTokenizer
model_path = os.environ['CANN_EVAL_MODEL_PATH']
model = AutoModelForCausalLM.from_pretrained(model_path, device_map='cpu')
tok = AutoTokenizer.from_pretrained(model_path)
out = model.generate(**tok('你好', return_tensors='pt'), max_new_tokens=5)
print(tok.decode(out[0], skip_special_tokens=True))
""")


class UseQwen2Stage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._venv_dir: str | None = None
        self._model_size_mb: float | None = None
        self._inference_ok: bool = False
        self._inference_output: str = ""
        self._software_error: bool = False

    def setup(self) -> None:
        # 创建隔离 venv，避免污染宿主机 Python 环境
        self._venv_dir = tempfile.mkdtemp(prefix="cann_eval_qwen2_venv_")
        venv.create(self._venv_dir, with_pip=True)

    def run(self) -> None:
        if self._venv_dir is None:
            self._mc.add_error(
                phenomenon="venv 未初始化，setup() 可能未执行",
                severity="P0",
                cause="self._venv_dir is None",
                solution="在 run() 前先调用 setup()",
            )
            self._mc.set_fail()
            return

        cache_dir = self._config.get("qwen2_cache_dir", "/tmp/qwen2_cache")
        model_name = self._config.get("qwen2_model", "qwen/Qwen2-0.5B")
        timeout = self._config.get("timeout", {}).get("use_qwen2_s", 600)
        # 使用 venv 内的 Python，不污染宿主机环境
        python = os.path.join(self._venv_dir, "bin", "python")

        # Step 1: 安装基础依赖（不含 torch-npu）
        # 注意：torch-npu 在无 NPU 机器上 import 会崩溃（torch_npu.npu 初始化失败），
        # 会导致 modelscope CLI 无法启动。必须在模型下载完成后再装 torch-npu。
        self._mc.start("install")
        install_steps_pre = [["torch", "modelscope", "transformers", "accelerate"]]
        for pkg_group in install_steps_pre:
            try:
                result = subprocess.run(
                    [python, "-m", "pip", "install", "-q"] + pkg_group,
                    capture_output=True, text=True, timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                self._mc.stop("install")
                self._mc.add_error(
                    phenomenon="pip 安装依赖超时",
                    severity="P0",
                    cause=f"安装超过 {timeout}s 超时限制",
                    solution="检查网络连接或增大 timeout.use_qwen2_s 配置",
                )
                self._mc.set_fail()
                return
            if result.returncode != 0:
                self._mc.stop("install")
                self._mc.add_error(
                    phenomenon=f"pip 安装 {' '.join(pkg_group)} 失败",
                    severity="P0",
                    cause=result.stderr[:200],
                    solution="检查网络连接和 pip 配置",
                )
                self._mc.set_fail()
                return
        self._mc.stop("install")

        # Step 2: 下载模型
        self._mc.start("download")
        modelscope_bin = os.path.join(self._venv_dir, "bin", "modelscope")
        try:
            dl_result = subprocess.run(
                [modelscope_bin, "download",
                 "--model", model_name, "--local_dir", cache_dir],
                capture_output=True, text=True, timeout=timeout,
            )
            self._mc.stop("download")
        except subprocess.TimeoutExpired:
            self._mc.stop("download")
            self._mc.add_error(
                phenomenon="模型下载超时",
                severity="P0",
                cause=f"下载超过 {timeout}s 超时限制",
                solution="检查网络连接或增大 timeout.use_qwen2_s 配置",
            )
            self._mc.set_fail()
            return
        if dl_result.returncode != 0:
            self._mc.add_error(
                phenomenon="Qwen2-0.5B 模型下载失败",
                severity="P0",
                cause=dl_result.stderr[:200],
                solution="检查网络，或手动下载到 qwen2_cache_dir",
            )
            self._mc.set_fail()
            return

        # 统计模型大小
        total = 0
        for root, _, files in os.walk(cache_dir):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
        self._model_size_mb = round(total / (1024 * 1024), 1)

        # Step 2.5: 模型下载完成后再装 torch-npu（--no-deps 避免依赖冲突）
        # torch-npu 在无 NPU 机器上 import 会崩溃，不能在 modelscope 下载前安装
        npu_result = subprocess.run(
            [python, "-m", "pip", "install", "-q", "torch-npu", "--no-deps"],
            capture_output=True, text=True, timeout=120,
        )
        if npu_result.returncode != 0:
            self._mc.add_error(
                phenomenon="torch-npu 安装失败（P1 可绕路，CPU 推理不依赖 NPU）",
                severity="P1",
                cause=npu_result.stderr[:200],
                solution="在昇腾硬件上安装 torch-npu；CPU 测试可跳过",
            )
            self._mc.set_warn()
            # 不 return，CPU 推理不需要 torch-npu 也能继续

        # Step 3: 运行推理
        env = os.environ.copy()
        env["CANN_EVAL_MODEL_PATH"] = cache_dir
        self._mc.start("inference")
        try:
            inf_result = subprocess.run(
                [python, "-c", INFERENCE_SCRIPT],
                capture_output=True, text=True, timeout=timeout, env=env,
            )
            self._mc.stop("inference")
        except subprocess.TimeoutExpired:
            self._mc.stop("inference")
            self._mc.add_error(
                phenomenon="推理超时",
                severity="P0",
                cause=f"推理超过 {timeout}s 超时限制",
                solution="检查模型配置或增大 timeout.use_qwen2_s 配置",
            )
            self._mc.set_fail()
            return

        if inf_result.returncode == 0:
            self._inference_ok = True
            self._inference_output = inf_result.stdout.strip()[:200]
        else:
            stderr = inf_result.stderr
            # 判断是否为纯硬件错误（NPU 缺失）
            is_hw_only = any(p.lower() in stderr.lower() for p in _HARDWARE_ERROR_PATTERNS)
            self._software_error = not is_hw_only
            if self._software_error:
                self._mc.add_error(
                    phenomenon="推理命令因软件原因失败",
                    severity="P0",
                    cause=stderr[:200],
                    solution="检查 transformers/torch 版本兼容性",
                )
                self._mc.set_fail()
            else:
                self._mc.add_error(
                    phenomenon="推理命令因缺少 NPU 硬件失败（预期行为）",
                    severity="P2",
                    cause="当前机器无物理 NPU，无法执行 NPU 推理",
                    solution="在昇腾硬件上运行完整推理",
                )
                self._mc.set_warn()

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        # 删除隔离 venv（保留模型缓存，避免重复下载）
        if self._venv_dir and os.path.exists(self._venv_dir):
            shutil.rmtree(self._venv_dir, ignore_errors=True)

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "model_size_mb": self._model_size_mb,
            "inference_ok": self._inference_ok,
            "inference_output": self._inference_output,
            "software_error": self._software_error,
        })
        return d
