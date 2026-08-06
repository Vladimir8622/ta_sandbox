import optuna
import subprocess
import json
import yaml
from functools import partial
import argparse
import importlib.util
import sys

def load_config(config_path: str) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def run_optimization(config):

    # Узнаем у стратегии основную инфу
    strategy_info = config['strategy_info']

    instruments_metainfo = config['instruments_metainfo']
    data_params = config['instruments']

    spec = importlib.util.spec_from_file_location("my_module", strategy_info['path'])
    module = importlib.util.module_from_spec(spec)
    sys.modules["my_module"] = module
    spec.loader.exec_module(module)

    MyClass = getattr(module, strategy_info['name'])

    # насколько это необходимо???
    necessary_instr_num = MyClass.get_data_requirements()['num_of_instrument']

    # Внимательно тут надо смотреть, что сообщаем и кому.
    if len(data_params) != 1 and necessary_instr_num == 'single':
        raise ValueError("incorrect num of instrument for this strategy")

    strategy_params = MyClass.get_strategy_params()

    # Ручками настраиваем брокера
    brokers_params = config['brokers']

    def objective(trial,instruments_metainfo,data_params,brokers_params,strategy_params, strategy_info):
        # Распаковываем массив параметров
        suggested = {}
        for row in strategy_params:
            name = row['name']
            if row['type'] == 'int':
                suggested[name] = trial.suggest_int(name, row['min'], row['max'])
            elif row['type'] == 'float':
                suggested[name] = trial.suggest_float(name, row['min'], row['max'])
            else:
                raise ValueError('incorrect strategy params')

        all_params = {
            'instruments_metainfo': instruments_metainfo,
            'instruments': data_params,
            'brokers': brokers_params,
            'strategy': suggested,
            'info': strategy_info
        }
        
        command = [sys.executable, 'core/engine.py', '--params', json.dumps(all_params)]
        
        result = subprocess.run(command, capture_output=True, text=True)

        # Проверка хахахахахахаха
        if result.returncode != 0:
            raise RuntimeError(f"Engine.py failed with code {result.returncode}\n{result.stderr}")

        output = json.loads(result.stdout)

        # Извлекаем метрики из вывода
        metric1 = output['total_return']
        metric2 = output['sharp_ratio']
        metric3 = output['max_drawdown']
        
        # логгирование процесса
        print(f"Trial {trial.number}: params={suggested}, metrics={metric1:.4f}, {metric2:.4f}, {metric3:.4f}")

        return metric1, metric2, metric3 # для многокритериального подхода

    study = optuna.create_study(directions=['maximize','maximize','minimize'])
    my_objective = partial(objective,
                           instruments_metainfo = instruments_metainfo,
                            data_params = data_params,
                            brokers_params = brokers_params,
                            strategy_params = strategy_params,
                            strategy_info = strategy_info
                            )
    study.optimize(my_objective, n_trials=100)

    successful_trials = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE and t.values is not None]

    if successful_trials:
        best_params = {
            'best_by_return': {
                'params': max(successful_trials, key=lambda t: t.values[0]).params,
                'metrics': {
                    'total_return': max(successful_trials, key=lambda t: t.values[0]).values[0],
                    'sharp_ratio': max(successful_trials, key=lambda t: t.values[0]).values[1],
                    'max_drawdown': max(successful_trials, key=lambda t: t.values[0]).values[2]
                }
            },
            'best_by_sharpe': {
                'params': max(successful_trials, key=lambda t: t.values[1]).params,
                'metrics': {
                    'total_return': max(successful_trials, key=lambda t: t.values[1]).values[0],
                    'sharp_ratio': max(successful_trials, key=lambda t: t.values[1]).values[1],
                    'max_drawdown': max(successful_trials, key=lambda t: t.values[1]).values[2]
                }
            },
            'best_by_drawdown': {
                'params': min(successful_trials, key=lambda t: t.values[2]).params,
                'metrics': {
                    'total_return': min(successful_trials, key=lambda t: t.values[2]).values[0],
                    'sharp_ratio': min(successful_trials, key=lambda t: t.values[2]).values[1],
                    'max_drawdown': min(successful_trials, key=lambda t: t.values[2]).values[2]
                }
            }
        }
        
        with open('best_params.json', 'w') as f:
            json.dump(best_params, f, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Single run of trading engine")
    parser.add_argument('--config', type=str, 
                        default=r'configs\optimization\portfolio_strategy.yaml',
                        help='Path to YAML configuration file')
    args = parser.parse_args()
 
    config = load_config(args.config)
    run_optimization(config)