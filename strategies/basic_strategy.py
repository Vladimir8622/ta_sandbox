from abc import ABC, abstractmethod
from responses.basic_response import Response

class Basic_Strategy(ABC):

    @property
    @abstractmethod
    def min_data_length(self) -> int:
        pass

    @abstractmethod
    def make_decision(self, data) -> Response:
        pass

    @abstractmethod
    def get_data_requirements(self) -> dict:
        pass

    @abstractmethod
    def get_strategy_params(self) -> list[dict]:
        pass