import inspect
import itertools

import pytest

from strategies.basic_strategy import Basic_Strategy
from strategies.demo_strategy import DemoStrategy
from strategies.ma_cross import MA_cross
from strategies.portfolio_strategy import Portfolio_strategy


ALL_STRATEGIES = [DemoStrategy, MA_cross, Portfolio_strategy]

# пока не сделано. на сколько частей делится сетка
_SAMPLE_POINTS = 3


def _sample_values(spec):
    lo, hi = spec['min'], spec['max']
    if spec['type'] == 'int':
        raw = {int(lo), int(round((lo + hi) / 2)), int(hi)}
    elif spec['type'] == 'float':
        raw = {float(lo), (lo + hi) / 2, float(hi)}
    else:
        raise AssertionError(f"неизвестный тип параметра: {spec['type']!r}")
    return sorted(raw)

def _param_grid(strategy_cls):
    specs = strategy_cls.get_strategy_params()
    names = [s['name'] for s in specs]
    options = [_sample_values(s) for s in specs]
    for combo in itertools.product(*options):
        yield dict(zip(names, combo))

def _min_valid_kwargs(strategy_cls):
    return {spec['name']: spec['min'] for spec in strategy_cls.get_strategy_params()}


@pytest.mark.parametrize('strategy_cls', ALL_STRATEGIES, ids=lambda c: c.__name__)
class TestStrategyContract:

    # наследие

    def test_is_basic_strategy_subclass(self, strategy_cls):
        assert issubclass(strategy_cls, Basic_Strategy)

    def test_all_abstractmethods_implemented(self, strategy_cls):
        assert not inspect.isabstract(strategy_cls), (
            f"{strategy_cls.__name__} не реализует все abstractmethod "
            f"из Basic_Strategy"
        )

    # get_strategy_params

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
        assert len(full_kwargs) > 0

        for name in full_kwargs:
            partial = {k: v for k, v in full_kwargs.items() if k != name}
            with pytest.raises(ValueError):
                strategy_cls(**partial)

    # get_data_requirements

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

    # min_data_length

    def test_min_data_length_across_param_grid(self, strategy_cls):
        combos = list(_param_grid(strategy_cls))
        assert combos, f"{strategy_cls.__name__}: сетка параметров пуста"

        failures = []
        for kwargs in combos:
            try:
                strategy = strategy_cls(**kwargs)
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