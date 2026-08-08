import numpy as np
from numba import njit
import sys

from strategies.basic_strategy import Basic_Strategy
from responses.instrument_response.instr_open_position import Open_Position
from responses.instrument_response.instr_modify_position import Modify_Position

from responses.global_response.wait import Wait
from responses.instrument_response.instr_wait import instr_Wait
from responses.global_response.close_all import Close_all
from responses.global_response.mixed_response import Mixed_response

import pandas as pd
from sklearn.model_selection import train_test_split
from skfolio import Population, RiskMeasure
from skfolio.preprocessing import prices_to_returns
from skfolio.optimization import MeanRisk, ObjectiveFunction
import logging

class Portfolio_strategy(Basic_Strategy):

    def __init__(self,**kwargs):
        super().__init__()

        required = {'rebalance_period','max_lot'}
        missing = required - set(kwargs.keys())
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")

        self.rebalance_period = kwargs['rebalance_period']
        self.max_lot = kwargs['max_lot']

        self.logger = logging.getLogger(kwargs['main_logger_name'] + '.' + __name__ + '.' + self.__class__.__name__)

        self.bar_count = 1           
        self.instruments = 'test'

    @property
    def min_data_length(self):
        return 300
    
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

    def make_decision(self, data):
        if self.instruments == 'test':
            all_level0 = data.columns.get_level_values(0).tolist()
            self.instruments = [name for name in all_level0 if name != 'current_state']

        is_rebalance_day = (self.bar_count % self.rebalance_period == 0)

        self.bar_count += 1

        if not is_rebalance_day:
            return Wait()
        
     
        

        self.logger.debug('Вернул не Wait')

        data_to_process = data.copy()
        prices = data_to_process.xs('close', level=1, axis=1)


        log_ret = prices_to_returns(prices)

        log_ret = log_ret.dropna() 

        # 1. Удаляем активы с нулевой дисперсией
        variances = log_ret.var()
        active_assets = variances[variances > 1e-10].index
        log_ret = log_ret[active_assets]
        X_train, X_test = train_test_split(log_ret, test_size=0.33, shuffle=False)
        train_var = X_train.var()
        train_active = train_var[train_var > 1e-10].index
        X_train = X_train[train_active]
        X_test = X_test[train_active]
        model_long_only = MeanRisk(
            risk_measure=RiskMeasure.VARIANCE,
            objective_function=ObjectiveFunction.MAXIMIZE_UTILITY,
            risk_aversion=1.0,
            min_weights=0.0,
            max_weights=1,
            portfolio_params=dict(name="Long-Only Max Sharpe"),
            solver="CLARABEL"
        )
        model_long_only.fit(X_train)
        pred_long_only = model_long_only.predict(X_test)
        weights = pred_long_only.weights_dict

        current_state = data_to_process['current_state'].iloc[-2]
        balance = current_state.balance
        last_prices = data_to_process.xs('close', level=1, axis=1).iloc[-1]

        decisions = {}
        for instrument in self.instruments:
            weight = weights.get(instrument, 0)
            price = last_prices.get(instrument)

            target_money = weight * balance if weight > 0 else 0

            position = current_state.positions.get(instrument)

            if position is not None:
                decisions[instrument] = Modify_Position(
                    direction=1,
                    new_volume=target_money,
                    entry_price=price,
                    take_profit=float('inf'),
                    stop_loss=0
                )
            else:
                if target_money > 0:
                    decisions[instrument] = Open_Position(
                        direction=1,
                        volume=target_money,
                        entry_price=price,
                        take_profit=float('inf'),
                        stop_loss=0
                    )
                else:
                    decisions[instrument] = instr_Wait()

            
        return Mixed_response(decisions)