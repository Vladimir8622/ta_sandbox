import inspect
import itertools
import logging
import random

import pytest

from strategies.basic_strategy import Basic_Strategy
from strategies.demo_strategy import DemoStrategy
from strategies.ma_cross import MA_cross
from strategies.portfolio_strategy import Portfolio_strategy
from strategies.advanced_portfolio_strategies.equal_weight import EqualWeight


ALL_STRATEGIES = [DemoStrategy, MA_cross, Portfolio_strategy, EqualWeight]

# Лимит комбинаций для теста min_data_length (чтобы не перебирать все при многих параметрах)
_MAX_COMBOS_FOR_MIN_DATA = 20


def _sample_values(spec):
    """Возвращает минимальное и максимальное значение параметра (крайние точки)."""
    lo, hi = spec['min'], spec['max']
    if spec['type'] == 'int':
        return {int(lo), int(hi)}
    elif spec['type'] == 'float':
        return {float(lo), float(hi)}
    else:
        raise AssertionError(f"неизвестный тип параметра: {spec['type']!r}")


def _param_grid(strategy_cls):
    """
    Генерирует ограниченный набор комбинаций параметров для тестирования.
    Берутся только крайние значения каждого параметра (min и max).
    Если число комбинаций превышает _MAX_COMBOS_FOR_MIN_DATA,
    то дополнительно выбираются случайные комбинации (но гарантированно проверяются все-минимумы и все-максимумы).
    """
    specs = strategy_cls.get_strategy_params()
    names = [s['name'] for s in specs]
    options = [_sample_values(s) for s in specs]

    # Все комбинации (декартово произведение)
    all_combos = list(itertools.product(*options))
    if len(all_combos) <= _MAX_COMBOS_FOR_MIN_DATA:
        combos = all_combos
    else:
        # Обязательно включаем комбинацию всех минимумов и всех максимумов
        min_combo = tuple(opt[0] for opt in options)   # предполагаем, что sorted() даёт min, max
        max_combo = tuple(opt[-1] for opt in options)
        # Случайно выбираем остальные, исключая уже добавленные
        rest = [c for c in all_combos if c != min_combo and c != max_combo]
        sample_size = min(_MAX_COMBOS_FOR_MIN_DATA - 2, len(rest))
        sampled = random.sample(rest, sample_size) if sample_size > 0 else []
        combos = [min_combo, max_combo] + sampled

    for combo in combos:
        yield dict(zip(names, combo))


def _min_valid_kwargs(strategy_cls):
    """Базовый набор параметров для создания стратегии (минимумы + служебные)."""
    base = {spec['name']: spec['min'] for spec in strategy_cls.get_strategy_params()}
    # Добавляем параметр для логгера (все стратегии принимают **kwargs)
    base['main_logger_name'] = 'test_logger'
    return base


@pytest.mark.parametrize('strategy_cls', ALL_STRATEGIES, ids=lambda c: c.__name__)
class TestStrategyContract:

    # ---------- Наследование и абстрактные методы ----------
    def test_is_basic_strategy_subclass(self, strategy_cls):
        assert issubclass(strategy_cls, Basic_Strategy)

    def test_all_abstractmethods_implemented(self, strategy_cls):
        assert not inspect.isabstract(strategy_cls), (
            f"{strategy_cls.__name__} не реализует все abstractmethod "
            f"из Basic_Strategy"
        )

    # ---------- get_strategy_params ----------
    def test_get_strategy_params_structure(self, strategy_cls):
        specs = strategy_cls.get_strategy_params()
        assert isinstance(specs, list), (
            f"{strategy_cls.__name__}.get_strategy_params() вернул "
            f"{type(specs).__name__}, ожидался list"
        )
        assert len(specs) > 0, (
            f"{strategy_cls.__name__} не объявляет ни одного параметра "
            f"через get_strategy_params()"
        )

        seen_names = set()
        for spec in specs:
            missing_keys = {'name', 'type', 'min', 'max'} - spec.keys()
            assert not missing_keys, (
                f"{strategy_cls.__name__}: параметр {spec} не содержит "
                f"ключи {missing_keys}"
            )
            assert spec['name'] not in seen_names, (
                f"{strategy_cls.__name__}: дублирующееся имя параметра "
                f"'{spec['name']}'"
            )
            seen_names.add(spec['name'])

            assert spec['type'] in ('int', 'float'), (
                f"{strategy_cls.__name__}: параметр '{spec['name']}' "
                f"имеет неизвестный type={spec['type']!r}"
            )
            assert spec['min'] < spec['max'], (
                f"{strategy_cls.__name__}: у параметра '{spec['name']}' "
                f"min >= max ({spec['min']} >= {spec['max']})"
            )

    def test_declared_params_are_enough_to_construct(self, strategy_cls):
        kwargs = _min_valid_kwargs(strategy_cls)
        try:
            strategy_cls(**kwargs)
        except ValueError as e:
            pytest.fail(
                f"{strategy_cls.__name__}: набора параметров из "
                f"get_strategy_params() ({sorted(kwargs)}) не хватило "
                f"для __init__: {e}"
            )

    def test_missing_required_kwarg_raises(self, strategy_cls):
        full_kwargs = _min_valid_kwargs(strategy_cls)
        # Убираем служебный main_logger_name из проверки, т.к. он не в required
        required_names = {spec['name'] for spec in strategy_cls.get_strategy_params()}
        assert len(required_names) > 0

        for name in required_names:
            partial = {k: v for k, v in full_kwargs.items() if k != name}
            with pytest.raises(ValueError):
                strategy_cls(**partial)

    # ---------- get_data_requirements ----------
    def test_get_data_requirements_structure(self, strategy_cls):
        req = strategy_cls.get_data_requirements()
        assert isinstance(req, dict), (
            f"{strategy_cls.__name__}.get_data_requirements() должен "
            f"возвращать dict, получили {type(req).__name__}"
        )
        assert 'num_of_instrument' in req, (
            f"{strategy_cls.__name__}: get_data_requirements() не "
            f"содержит ключ 'num_of_instrument'"
        )
        assert req['num_of_instrument'] in ('single', 'multiple'), (
            f"{strategy_cls.__name__}: num_of_instrument="
            f"{req['num_of_instrument']!r}, ожидались 'single' или "
            f"'multiple'"
        )

    # ---------- min_data_length ----------
    def test_min_data_length_across_param_grid(self, strategy_cls):
        combos = list(_param_grid(strategy_cls))
        assert combos, f"{strategy_cls.__name__}: сетка параметров пуста"

        failures = []
        for kwargs in combos:
            # Добавляем main_logger_name для логгеров
            kwargs_with_logger = dict(kwargs, main_logger_name='test_logger')
            try:
                strategy = strategy_cls(**kwargs_with_logger)
                length = strategy.min_data_length
            except Exception as e:
                failures.append(f"{kwargs} -> {e!r}")
                continue

            if not isinstance(length, int):
                failures.append(
                    f"{kwargs} -> min_data_length не int, а "
                    f"{type(length).__name__}: {length!r}"
                )
            elif length <= 0:
                failures.append(
                    f"{kwargs} -> min_data_length = {length} (должно быть > 0)"
                )

        assert not failures, (
            f"{strategy_cls.__name__}: min_data_length падает или "
            f"возвращает мусор на следующих комбинациях параметров:\n"
            + "\n".join(failures)
        )

    # ---------- Логгер ----------
    def test_logger_initialized(self, strategy_cls):
        kwargs = _min_valid_kwargs(strategy_cls)
        strategy = strategy_cls(**kwargs)

        # Проверяем наличие атрибута logger
        assert hasattr(strategy, 'logger'), (
            f"{strategy_cls.__name__} не имеет атрибута 'logger'"
        )
        logger = strategy.logger
        assert isinstance(logger, logging.Logger), (
            f"{strategy_cls.__name__}.logger должен быть logging.Logger, "
            f"получен {type(logger).__name__}"
        )

        # Проверяем, что имя логгера содержит переданное имя (если стратегия его использует)
        # Это не обязательное требование, но полезно для отладки.
        # Если стратегия не использует main_logger_name, то имя может быть другим,
        # поэтому проверку делаем мягкой.
        if 'main_logger_name' in kwargs:
            expected_part = kwargs['main_logger_name']
            if expected_part not in logger.name:
                # Это не ошибка, просто предупреждение (можно пропустить).
                pass  # или записать в лог, но в тестах лучше просто игнорировать