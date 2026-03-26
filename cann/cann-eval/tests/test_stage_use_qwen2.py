# tests/test_stage_use_qwen2.py
import pytest
from unittest.mock import patch, MagicMock
from stages.stage_use_qwen2 import UseQwen2Stage

BASE_CONFIG = {
    "qwen2_model": "qwen/Qwen2-0.5B",
    "qwen2_source": "modelscope",
    "qwen2_cache_dir": "/tmp/test_qwen2",
    "timeout": {"use_qwen2_s": 60},
}

def _make_stage(config=None):
    return UseQwen2Stage(config or BASE_CONFIG)

def _setup_stage(stage):
    """Helper: call setup() with venv mocked out."""
    with patch("stages.stage_use_qwen2.venv.create"), \
         patch("stages.stage_use_qwen2.tempfile.mkdtemp", return_value="/tmp/test_venv"):
        stage.setup()

def test_qwen2_inference_success():
    stage = _make_stage()
    _setup_stage(stage)
    with patch("stages.stage_use_qwen2.subprocess.run") as mock_run, \
         patch("stages.stage_use_qwen2.os.walk", return_value=[("/tmp/test_qwen2", [], ["model.safetensors"])]), \
         patch("stages.stage_use_qwen2.os.path.getsize", return_value=1024 * 1024 * 1000):
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr=""),     # pip install
            MagicMock(returncode=0, stderr=""),     # modelscope download
            MagicMock(returncode=0, stdout="你好，我是 Qwen2", stderr=""),  # inference
        ]
        stage.run()
    assert stage.verify() is True
    m = stage.metrics()
    assert m["inference_ok"] is True
    assert m["model_size_mb"] == round(1000.0, 1)  # 1000 MB

def test_qwen2_inference_failure_software_error():
    stage = _make_stage()
    _setup_stage(stage)
    with patch("stages.stage_use_qwen2.subprocess.run") as mock_run, \
         patch("stages.stage_use_qwen2.os.path.getsize", return_value=1024):
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr=""),    # pip install
            MagicMock(returncode=0, stderr=""),    # modelscope download
            MagicMock(returncode=1, stdout="", stderr="ImportError: No module named 'xxx'"),
        ]
        stage.run()
    m = stage.metrics()
    assert m["inference_ok"] is False
    assert m["software_error"] is True

def test_qwen2_inference_failure_hardware_only():
    stage = _make_stage()
    _setup_stage(stage)
    with patch("stages.stage_use_qwen2.subprocess.run") as mock_run, \
         patch("stages.stage_use_qwen2.os.path.getsize", return_value=1024):
        mock_run.side_effect = [
            MagicMock(returncode=0, stderr=""),
            MagicMock(returncode=0, stderr=""),
            MagicMock(returncode=1, stdout="", stderr="RuntimeError: No NPU device found"),
        ]
        stage.run()
    m = stage.metrics()
    assert m["inference_ok"] is False
    assert m["software_error"] is False  # NPU 缺失属于预期行为，不是软件错误
    assert stage.verify() is True

def test_qwen2_teardown_removes_venv():
    stage = _make_stage()
    _setup_stage(stage)
    with patch("stages.stage_use_qwen2.shutil.rmtree") as mock_rm, \
         patch("stages.stage_use_qwen2.os.path.exists", return_value=True):
        stage.teardown()
    mock_rm.assert_called_once_with("/tmp/test_venv", ignore_errors=True)
