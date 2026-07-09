from abc import ABC, abstractmethod
from Responses.Basic_Response import Response
from State import State as State

class Basic_Broker(ABC):
    @abstractmethod
    def check_response(self,current_state,response) -> State:
        pass

    @abstractmethod
    def check_position(self, current_state, data) -> State:
        pass