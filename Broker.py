import pandas as pd
import Response
import State
import Position

class Broker:
    def __init__(self, commissions, slippage):
        self.commissions = commissions
        self.slippage = slippage
    def get_commissions(self, name):
        return self.commissions
    def get_slippage(self, name):
        return self.slippage
    def check_response(self,current_state,response):
        new_state = current_state.copy()

        if response.get_direction() == 1:
            new_state.balance -= response.volume * (1 + self.commissions + self.slippage)
            position = Position(1)
            new_state.positions.append(position)
        elif response.get_direction() == -1:
            new_state.balance -= response.volume * (1 + self.commissions + self.slippage)
            position = Position(-1)
            new_state.positions.append(position)
        else:
            pass

        return new_state
    
     
