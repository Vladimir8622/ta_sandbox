from Strategies.Basic_Strategy import Basic_Strategy
from Responses.Open_Position import Open_Position
from Responses.Wait import Wait


class MA_cross(Basic_Strategy):
    def __init__(self, long_period,short_period,take_profit_percent,stop_loss_percent):
        super().__init__()
        self.long_period = long_period
        self.short_period = short_period
        self.take_profit_percent = take_profit_percent
        self.stop_loss_percent = stop_loss_percent

    
    @staticmethod
    def get_data_params():
        Market = "MOEX"
        Active = "adjusted_stock"
        Timeframe = "1d"
        Name = "ABIO.MOEX"
        Start = "2023-08-18"
        End = "2026-07-08"
        data_params = {
            'Market': Market,
            'Active': Active,
            'Timeframe': Timeframe,
            'Name': Name,
            'Start': Start,
            'End': End
        }
        return data_params
    
    @staticmethod
    def get_strategy_params():
        return [
            {'name': 'long_period', 'type': 'int', 'min': 50, 'max': 500},
            {'name': 'short_period', 'type': 'int', 'min': 5, 'max': 45},
            {'name': 'take_profit_percent', 'type': 'float', 'min': 0.001, 'max': 1},
            {'name': 'stop_loss_percent', 'type': 'float', 'min': 0.001, 'max': 1},
        ]

    def get_min_data_length(self):
        return max(self.long_period, self.short_period) + 1

    def make_decision(self, data):
        data_to_process = data.copy()
        # calculating MA
        data_to_process['long_MA'] = data_to_process['close'].rolling(window=self.long_period).mean()
        data_to_process['short_MA'] = data_to_process['close'].rolling(window=self.short_period).mean()
        data_to_process['delta'] = data_to_process['long_MA'] - data_to_process['short_MA']
        
        data_to_process = data_to_process.dropna(subset=['delta'])

        # Берём два последних значения (индексы -1 и -2)
        delta_last = data_to_process['delta'].iloc[-1]
        delta_prev = data_to_process['delta'].iloc[-2]


        if delta_last > 0 and delta_prev < 0:
            balance = data_to_process['current_state'].iloc[-1].balance
            price = data_to_process['close'].iloc[-1]
            return Open_Position(1,balance,price, take_profit = price*(1+self.take_profit_percent), stop_loss = price *(1-self.stop_loss_percent))
        elif delta_last < 0 and delta_prev > 0:
            balance = data_to_process['current_state'].iloc[-1].balance
            price = data_to_process['close'].iloc[-1]
            return Open_Position(-1,balance,price, take_profit = price*(1-self.take_profit_percent), stop_loss = price *(1+self.stop_loss_percent))
        else:
            return Wait()