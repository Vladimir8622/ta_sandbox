from Strategies.Basic_Strategy import Basic_Strategy
from Responses.Open_Position import Open_Position
from Responses.Wait import Wait
import random


class Test_strategy(Basic_Strategy):
    def __init__(self, take_profit_percent,stop_loss_percent):
        super().__init__()
        self.take_profit_percent = take_profit_percent
        self.stop_loss_percent = stop_loss_percent

        self.Name = "GD_5min"

    @staticmethod
    def get_data_params():
        Market = "MOEX"
        Active = "adjusted_stock"
        Timeframe = "1d"
        Name = "GD_5min"
        Start = "2023-08-18"
        End = "2026-07-08"
        data_params = [{
            'Market': Market,
            'Active': Active,
            'Timeframe': Timeframe,
            'Name': Name,
            'Start': Start,
            'End': End
        }]
        return data_params
    
    @staticmethod
    def get_strategy_params():
        return [
            {'name': 'take_profit_percent', 'type': 'float', 'min': 0.001, 'max': 1},
            {'name': 'stop_loss_percent', 'type': 'float', 'min': 0.001, 'max': 1},
        ]

    def get_min_data_length(self):
        return 1

    def make_decision(self, data):
        data_to_process = data.copy()
        value = random.choice([-1, 0, 1])
        if value == -1:
            balance = data_to_process['current_state'].iloc[-2].balance
            price = price = data_to_process[self.Name]['close'].iloc[-2]
            decison = Open_Position(-1,1,price, take_profit = price*(1-self.take_profit_percent), stop_loss = price*(1+self.stop_loss_percent))
        elif value == 1:
            balance = data_to_process['current_state'].iloc[-2].balance
            price = price = data_to_process[self.Name]['close'].iloc[-2]
            decison = Open_Position(1,1,price, take_profit = price*(1+self.take_profit_percent), stop_loss = price*(1-self.stop_loss_percent))
        else:
            decison = Wait()
        
        return {self.Name:decison}