from abc import ABC, abstractmethod
from Responses.Basic_Response import Response

class Basic_Strategy(ABC):

    @abstractmethod
    def make_decision(self, data) -> Response:
        pass

    @abstractmethod
    def get_data_params(self) -> dict:
        pass

    @abstractmethod
    def get_strategy_params(self) -> dict:
        pass

    def get_min_data_length(self):
        return 100  # значение по умолчанию