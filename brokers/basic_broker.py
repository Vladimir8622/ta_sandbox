from abc import ABC, abstractmethod
from responses.basic_response import Response
from core.state import State as State

class Basic_Broker(ABC):
    @abstractmethod
    def mark_to_market(self, current_state, last_row) -> State:   # NEW
        pass
    
    @abstractmethod
    def check_response(self,current_state,response) -> State:
        pass

    @abstractmethod
    def check_position(self, current_state, data) -> State:
        pass