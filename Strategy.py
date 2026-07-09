import pandas as pd
import Response
import State
import Position

class Strategy:
    def __init__(self, params):
        self.params = params

    def make_decision(self, data, current_state):
        test = Response(1,data['close'].to_list()[-1],1)
        return test