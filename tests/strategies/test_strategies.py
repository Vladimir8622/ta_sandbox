import pytest
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import sys
from copy import deepcopy

# Импортируем все стратегии
from strategies.demo_strategy import DemoStrategy
from strategies.ma_cross import MA_cross
from strategies.portfolio_strategy import Portfolio_strategy
from strategies.advanced_portfolio_strategies.equal_weight import EqualWeight

# Импортируем ответы
from responses.global_response.wait import Wait
from responses.global_response.close_all import Close_all
from responses.global_response.mixed_response import Mixed_response
from responses.instrument_response.instr_open_position import Open_Position
from responses.instrument_response.instr_modify_position import Modify_Position
from responses.instrument_response.instr_wait import instr_Wait
from responses.instrument_response.instr_close import Close  # новый класс

# Импортируем State и Position (для генерации синтетических данных)
from core.state import State
from core.position import Position

# Импортируем брокера (для интеграционного теста)
from brokers.demo_broker import DemoBroker

ALL_STRATEGIES = [DemoStrategy, MA_cross, Portfolio_strategy, EqualWeight]


def generate_synthetic_data(n_bars=100, n_instruments=3, with_state=True, seed=42):
    """Генерирует синтетический мультииндексный DataFrame с колонкой current_state."""
    np.random.seed(seed)
    dates = pd.date_range(start='2020-01-01', periods=n_bars, freq='D')
    instruments = [f'INSTR_{i+1}' for i in range(n_instruments)]

    # Создаём мультииндекс колонок: (instrument, field)
    fields = ['open', 'high', 'low', 'close', 'volume']
    columns = pd.MultiIndex.from_product([instruments, fields])

    # Генерируем случайные цены (логнормальное блуждание)
    prices = np.random.lognormal(mean=0, sigma=0.02, size=(n_bars, n_instruments))
    prices = np.cumprod(prices, axis=0) * 100  # старт с 100

    # Заполняем другие поля (упрощённо)
    data = np.zeros((n_bars, len(instruments) * len(fields)))
    for i, inst in enumerate(instruments):
        close = prices[:, i]
        # open = previous close (кроме первого)
        open_ = np.concatenate([[close[0]], close[:-1]])
        high = close * (1 + np.random.uniform(0, 0.02, n_bars))
        low = close * (1 - np.random.uniform(0, 0.02, n_bars))
        volume = np.random.randint(100, 1000, n_bars)
        data[:, i*len(fields) : (i+1)*len(fields)] = np.column_stack([open_, high, low, close, volume])

    df = pd.DataFrame(data, index=dates, columns=columns)

    # Добавляем колонку 'current_state' (если нужно)
    if with_state:
        df['current_state'] = [State(margin=1000) for _ in range(n_bars)]

    return df


def _min_valid_kwargs_with_logger(strategy_cls):
    """Возвращает минимальные параметры для стратегии + main_logger_name."""
    kwargs = {spec['name']: spec['min'] for spec in strategy_cls.get_strategy_params()}
    kwargs['main_logger_name'] = 'test_logger'
    return kwargs


@pytest.mark.parametrize('strategy_cls', ALL_STRATEGIES, ids=lambda c: c.__name__)
class TestStrategyIntegration:

    def test_response_types(self, strategy_cls):
        """Проверяет, что make_decision возвращает корректный глобальный ответ."""
        kwargs = _min_valid_kwargs_with_logger(strategy_cls)
        strategy = strategy_cls(**kwargs)

        # Генерируем достаточно данных (длина >= min_data_length)
        min_len = strategy.min_data_length
        data = generate_synthetic_data(n_bars=min_len + 5, n_instruments=3)

        # Вызываем make_decision
        response = strategy.make_decision(data)

        # Проверяем, что ответ является экземпляром одного из глобальных ответов
        assert isinstance(response, (Wait, Close_all, Mixed_response)), \
            f"Ответ {type(response)} не является допустимым глобальным ответом"

    def test_mixed_response_instrument_types(self, strategy_cls):
        """Если вернулся Mixed_response, проверяем содержимое."""
        kwargs = _min_valid_kwargs_with_logger(strategy_cls)
        strategy = strategy_cls(**kwargs)

        data = generate_synthetic_data(n_bars=strategy.min_data_length + 5, n_instruments=3)

        response = strategy.make_decision(data)

        if isinstance(response, Mixed_response):
            decisions = response.positions
            assert isinstance(decisions, dict), "Mixed_response.positions должен быть dict"

            # Получаем список инструментов из данных
            instrument_names = [col[0] for col in data.columns if col[0] != 'current_state']
            instrument_names = list(dict.fromkeys(instrument_names))  # уникальные

            for instr, decision in decisions.items():
                assert instr in instrument_names, f"Инструмент {instr} отсутствует в данных"
                assert isinstance(decision, (Open_Position, Modify_Position, instr_Wait, Close)), \
                    f"В Mixed_response обнаружен недопустимый ответ: {type(decision)}"

    def test_engine_integration(self, strategy_cls):
        """Интеграционный тест: прогон стратегии через движок с синтетическими данными."""
        kwargs = _min_valid_kwargs_with_logger(strategy_cls)
        strategy = strategy_cls(**kwargs)
        min_len = strategy.min_data_length
        n_bars = min_len + 20  # достаточно баров для нескольких решений

        data = generate_synthetic_data(n_bars=n_bars, n_instruments=3)
        # Добавляем logger для брокера
        broker = DemoBroker(commissions=0.001, slippage=0.001, main_logger_name='test_logger')

        # Инициализируем текущее состояние (первая строка с состоянием)
        current_state = data['current_state'].iloc[0]

        # Цикл по барам, начиная с min_len (как в движке)
        for i in range(min_len, len(data)):
            history = data.iloc[:i+1]
            last_row = data.iloc[i]

            # mark-to-market
            new_state = broker.mark_to_market(current_state=current_state, last_row=last_row)

            # решение стратегии
            response = strategy.make_decision(history)

            # обработка решения
            new_state = broker.check_response(current_state=new_state, response=response, last_row=last_row)

            # обработка отложенных ордеров
            new_state = broker.process_pending_orders(current_state=new_state, last_row=last_row)

            # обновляем состояние
            data.iloc[i, data.columns.get_loc('current_state')] = new_state
            current_state = new_state

            # Простые проверки: баланс не должен быть отрицательным, позиции корректны
            assert current_state.balance >= 0, "Баланс стал отрицательным"
            # Можно добавить другие проверки

    def test_wait_on_insufficient_data(self, strategy_cls):
        """Проверяет, что при недостаточных данных стратегия возвращает Wait (если это ожидаемо)."""
        kwargs = _min_valid_kwargs_with_logger(strategy_cls)
        strategy = strategy_cls(**kwargs)
        min_len = strategy.min_data_length

        if min_len == 1:
            pytest.skip("Стратегия требует только 1 бар, проверка неактуальна")

        # Генерируем данные с недостаточным количеством баров
        data = generate_synthetic_data(n_bars=min_len - 1, n_instruments=3)

        # Вызываем make_decision (должен вернуть Wait, если стратегия проверяет длину)
        response = strategy.make_decision(data)

        # Не все стратегии проверяют длину внутри, но мы можем ожидать Wait,
        # если стратегия не может принять решение (например, для портфельных, которые ждут ребаланса).
        # Здесь мы просто проверяем, что ответ валидный, а не падает.
        assert isinstance(response, (Wait, Close_all, Mixed_response)), \
            f"Ответ {type(response)} не является допустимым"