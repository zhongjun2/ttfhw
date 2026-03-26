import pytest
from stages.base import BaseStage

def test_base_stage_is_abstract():
    with pytest.raises(TypeError):
        BaseStage()

def test_concrete_stage_must_implement_all_methods():
    class Incomplete(BaseStage):
        pass
    with pytest.raises(TypeError):
        Incomplete()

def test_concrete_stage_can_be_instantiated():
    class Complete(BaseStage):
        def setup(self): pass
        def run(self): pass
        def verify(self) -> bool: return True
        def teardown(self): pass
        def metrics(self) -> dict: return {}
    stage = Complete()
    assert stage.verify() is True
