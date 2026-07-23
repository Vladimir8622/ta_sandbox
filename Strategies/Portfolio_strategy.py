import numpy as np
from numba import njit

from Strategies.Basic_Strategy import Basic_Strategy
from responses.instrument_response.instr_open_position import Open_Position
from responses.global_response.Wait import Wait
from responses.instrument_response.instr_wait import instr_Wait
from responses.global_response.Close_all import Close_all
from responses.global_response.Mixed_response import Mixed_response

import pandas as pd
from sklearn.model_selection import train_test_split
from skfolio import Population, RiskMeasure
from skfolio.preprocessing import prices_to_returns
from skfolio.optimization import MeanRisk, ObjectiveFunction


class Portfolio_strategy(Basic_Strategy):

    def __init__(self,rebalance_period,max_lot):
        super().__init__()
        self.rebalance_period = rebalance_period
        self.max_lot = max_lot
        self.bar_count = 0          
        self.target_weights = {}    
        self.instruments = 'test'
    
    @staticmethod
    def get_data_requirements():
        return {
            'num_of_instrument':'multiple'
        }

    @staticmethod
    def get_strategy_params():
        return [
            {'name': 'rebalance_period', 'type': 'int', 'min': 1, 'max': 500},
            {'name': 'max_lot', 'type': 'int', 'min': 5, 'max': 45}
        ]

    def get_min_data_length(self):
        return 100

    def make_decision(self, data):
        # only for the first usage of this func
        if self.instruments == 'test':
            all_level0 = data.columns.get_level_values(0).tolist()
            self.instruments = [name for name in all_level0 if name != 'current_state']

        pre_rebalance_day = ((self.bar_count+1) % self.rebalance_period == 0)
        is_rebalance_day = (self.bar_count % self.rebalance_period == 0)
        self.bar_count += 1

        if pre_rebalance_day:
            return Close_all()  

        if not is_rebalance_day:
            return Wait()    
               
        data_to_process = data.copy()
        prices = data_to_process.xs('close', level=1, axis=1)
        log_ret = prices_to_returns(prices)
        X_train, X_test = train_test_split(log_ret, test_size=0.33, shuffle=False)
        
        
        model_long_only = MeanRisk(
            risk_measure=RiskMeasure.VARIANCE,
            objective_function=ObjectiveFunction.MAXIMIZE_UTILITY,
            risk_aversion=1.0,
            min_weights=0.0,
            max_weights=1,
            portfolio_params=dict(name="Long-Only Max Sharpe"),
            solver="CLARABEL"        )
        model_long_only.fit(X_train)

        pred_long_only = model_long_only.predict(X_test)

        weights = pred_long_only.weights_dict
        
        current_state = data_to_process['current_state'].iloc[-1]
        balance = current_state.balance
        
        last_prices = data_to_process.xs('close', level=1, axis=1).iloc[-1]
        
        decisions = {}
        
        for instrument in self.instruments:
            weight = weights.get(instrument, 0)
            
            if weight <= 0:
                decisions[instrument] = instr_Wait()
            else:
                price = last_prices[instrument]
                
                volume = weight * balance
                
                decisions[instrument] = Open_Position(direction=1,  volume=volume,entry_price=price,take_profit=float('inf'), stop_loss=0)
        
        return Mixed_response(decisions)