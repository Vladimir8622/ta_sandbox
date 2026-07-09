from Strategies.Basic_Strategy import Basic_Strategy
from Responses.Open_Position import Open_Position


class MA_cross(Basic_Strategy):
    def __init__(self, long_period,short_period):
        super().__init__()
        self.long_period = long_period
        self.short_period = short_period
    
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
            return Open_Position(1,balance,price, price*1.1, price *0.9)
        else:
            return Open_Position(0,0,0, 0, 0)