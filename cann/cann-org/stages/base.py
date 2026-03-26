from abc import ABC, abstractmethod


class BaseStage(ABC):
    @abstractmethod
    def setup(self) -> None: ...

    @abstractmethod
    def run(self) -> None: ...

    @abstractmethod
    def verify(self) -> bool: ...

    @abstractmethod
    def teardown(self) -> None: ...

    @abstractmethod
    def metrics(self) -> dict: ...
