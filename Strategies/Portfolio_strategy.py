import numpy as np
from numba import njit

from Strategies.Basic_Strategy import Basic_Strategy
from Responses.Open_Position import Open_Position
from Responses.Wait import Wait

import pandas as pd
from sklearn.model_selection import train_test_split
from skfolio import Population, RiskMeasure
from skfolio.preprocessing import prices_to_returns
from skfolio.optimization import MeanRisk, ObjectiveFunction


class Portfolio(Basic_Strategy):

    def __init__(self):
        super().__init__()
        self.instruments = ["ABIO.MOEX", "ABRD.MOEX", "AFKS.MOEX"]  

    @staticmethod
    def get_data_params():
        data_params =  [
            {
                'Market': "MOEX",
                'Active': "adjusted_stock",
                'Timeframe': "1d",
                'Name': "ABIO.MOEX",
                'Start': "2023-08-18",
                'End': "2026-07-08"
            },
            {
                'Market': "MOEX",
                'Active': "adjusted_stock",
                'Timeframe': "1d",
                'Name': "ABRD.MOEX",
                'Start': "2023-08-18",
                'End': "2026-07-08"
            },
            {
                'Market': "MOEX",
                'Active': "adjusted_stock",
                'Timeframe': "1d",
                'Name': "AFKS.MOEX",
                'Start': "2023-08-18",
                'End': "2026-07-08"
            }
        ]
        return data_params
    
    # @staticmethod
    # def get_strategy_params():
    #     return [
    #         {'name': 'long_period', 'type': 'int', 'min': 50, 'max': 500},
    #         {'name': 'short_period', 'type': 'int', 'min': 5, 'max': 45},
    #         {'name': 'take_profit_percent', 'type': 'float', 'min': 0.001, 'max': 1},
    #         {'name': 'stop_loss_percent', 'type': 'float', 'min': 0.001, 'max': 1},
    #     ]

    def get_min_data_length(self):
        return 1

    def make_decision(self, data):
        data_to_process = data.copy()
        prices = data_to_process.xs('close', level=1, axis=1)
        log_ret = prices_to_returns(prices)
        X_train, X_test = train_test_split(log_ret, test_size=0.33, shuffle=False)
        
        
        model_long_only = MeanRisk(
            risk_measure=RiskMeasure.VARIANCE,
            objective_function=ObjectiveFunction.MAXIMIZE_RATIO,
            min_weights=0.0,
            max_weights=0.3,
            portfolio_params=dict(name="Long-Only Max Sharpe"),
        )
        model_long_only.fit(X_train)

        pred_long_only = model_long_only.predict(X_test)

        weights = pred_long_only.get_weights()
        
        current_state = data_to_process['current_state'].iloc[-1]
        balance = current_state.balance
        
        last_prices = data_to_process.xs('close', level=1, axis=1).iloc[-1]
        
        decisions = {}
        
        for instrument in self.instruments:
            weight = weights.get(instrument, 0)
            
            if weight <= 0:
                decisions[instrument] = Wait()
            else:
                price = last_prices[instrument]
                
                volume = weight * balance
                
                decisions[instrument] = Open_Position(direction=1,  volume=volume,entry_price=price,take_profit=float('inf'), stop_loss=0)
        
        return decisions