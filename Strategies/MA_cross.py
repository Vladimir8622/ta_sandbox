import numpy as np
from numba import njit

from Strategies.Basic_Strategy import Basic_Strategy
from Responses.Open_Position import Open_Position
from Responses.Wait import Wait


@njit(cache=True)
def _last_two_ma_deltas(close, long_period, short_period):

    n = close.shape[0]

    long_sum = 0.0
    for i in range(n - long_period, n):
        long_sum += close[i]
    long_ma_last = long_sum / long_period
    long_sum_prev = long_sum - close[n - 1] + close[n - 1 - long_period]
    long_ma_prev = long_sum_prev / long_period

    short_sum = 0.0
    for i in range(n - short_period, n):
        short_sum += close[i]
    short_ma_last = short_sum / short_period
    short_sum_prev = short_sum - close[n - 1] + close[n - 1 - short_period]
    short_ma_prev = short_sum_prev / short_period

    delta_last = long_ma_last - short_ma_last
    delta_prev = long_ma_prev - short_ma_prev
    return delta_last, delta_prev


class MA_cross(Basic_Strategy):

    def __init__(self, long_period,short_period,take_profit_percent,stop_loss_percent):
        super().__init__()
        self.long_period = long_period
        self.short_period = short_period
        self.take_profit_percent = take_profit_percent
        self.stop_loss_percent = stop_loss_percent

        self.Name = "test"
    
    @staticmethod
    def get_data_requirements():
        return {
            'num_of_instrument':'single'
        }

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
        # only for the first usage of this func
        if self.Name == 'test':
            all_level0 = data.columns.get_level_values(0).tolist()
            self.Name = [name for name in all_level0 if name != 'current_state'][0]

        data_to_process = data[self.Name]

        need = max(self.long_period, self.short_period) + 1
        close_tail = data_to_process['close'].iloc[-need:].to_numpy(dtype=np.float64)

        delta_last, delta_prev = _last_two_ma_deltas(close_tail, self.long_period, self.short_period)

        if delta_last > 0 and delta_prev < 0:
            balance = data['current_state'].iloc[-2].balance
            price = data_to_process['close'].iloc[-2]
            decison = Open_Position(1,balance,price, take_profit = price*(1+self.take_profit_percent), stop_loss = price *(1-self.stop_loss_percent))
        elif delta_last < 0 and delta_prev > 0:
            balance = data['current_state'].iloc[-2].balance
            price = data_to_process['close'].iloc[-2]
            decison = Open_Position(-1,balance,price, take_profit = price*(1-self.take_profit_percent), stop_loss = price *(1+self.stop_loss_percent))
        else:
            decison = Wait()
        
        return {self.Name:decison}