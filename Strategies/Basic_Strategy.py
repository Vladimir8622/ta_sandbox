from abc import ABC, abstractmethod
from Responses.Basic_Response import Response

class Basic_Strategy(ABC):
    
    @abstractmethod
    def make_decision(self, data) -> Response:
        pass