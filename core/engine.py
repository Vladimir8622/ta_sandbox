import sys
from pathlib import Path
if __name__ == "__main__":
    root_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(root_dir))

import data_management.data_manager as dm
from brokers.demo_broker import DemoBroker
from responses.global_response.close_all import Close_all
from responses.instrument_response.instr_open_position import Open_Position
from responses.global_response.wait import Wait
from responses.instrument_response.instr_wait import instr_Wait
from core.state import State
import argparse
import json
import pandas as pd
import sys
import importlib.util


import logging

def create_logs(response,new_state,datetime):
    # 1. Преобразуем решения (response) в словарь решений
    # decisions_dict = {}
    # for instrument, decision in response.items():
    #     if isinstance(decision, Wait):
    #         decisions_dict[instrument] = {'type': 'Wait'}
    #     elif isinstance(decision, Close_all):
    #         decisions_dict[instrument] = {'type': 'Close_all'}
    #     else:  # это Open_Position
    #         decisions_dict[instrument] = {
    #             'type': 'Open_Position',
    #             'direction': decision.direction,
    #             'volume': decision.volume,
    #             'entry_price': decision.entry_price,
    #             'take_profit': decision.take_profit,
    #             'stop_loss': decision.stop_loss
    #         }
    
    positions_dict = {}
    for instrument, pos in new_state.positions.items():
        positions_dict[instrument] = {
            'direction': pos.direction,
            'volume': pos.volume,
            'entry_price': pos.entry_price,
            'amount': pos.amount,
            'locked_volume': pos.locked_volume,
        }

    pending_orders_dict = []
    for order in new_state.pending_orders:
        pending_orders_dict.append({
                "symbol": order.symbol,
                "side": order.side,
                "volume": order.volume,
                "order_type": order.order_type,
                "limit_price": order.limit_price,
                "trigger_price": order.trigger_price,
                "linked_lot_id": order.linked_lot_id,
                "take_profit": order.take_profit,
                "stop_loss": order.stop_loss,
                "created_at": order.created_at
        })

    history_orders_dict = []
    for order in new_state.history_orders:
        history_orders_dict.append({
                "id": order.id,
                "symbol": order.symbol,
                "side": order.side,
                "order_type": order.order_type,
                "status": order.status,
                "volume": order.volume,
                "filled_price": order.filled_price,
                "filled_volume": order.filled_volume,
                "trigger_price": order.trigger_price,
                "linked_lot_id": order.linked_lot_id,
                "take_profit": order.take_profit,
                "stop_loss": order.stop_loss,
                "created_at": order.created_at,
                "filled_at": order.filled_at,
        })

    current_line = {
            'datetime': datetime,
            'balance': new_state.balance,
            'margin': new_state.margin,
            'positions': positions_dict,
            'pending_orders': pending_orders_dict,
            'history_orders': history_orders_dict,
        }
    return current_line

parser = argparse.ArgumentParser()
parser.add_argument('--params', type=str, required=True)
parser.add_argument('--logs', action='store_true')
args = parser.parse_args()
params = json.loads(args.params)

# Включаем логгирование для проверку результатов оптимизации
logger_name = 'ENGINE'
logger = logging.getLogger(logger_name)
logger.setLevel(logging.DEBUG)



if args.logs:
    print('Переходим в режим логгирования',file=sys.stderr, end = '---->')
    logs = []
    handler = logging.FileHandler(params['dir'] + '/' + 'test.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
else:
    logger.addHandler(logging.NullHandler())

#Загрузка даты
manager = dm.Data_manager()
data = []

if params['instruments_metainfo']['type'] == 'single':
    instruments = params['instruments']
    instrument_names = [instruments['Name']]

    timeframe = instruments['Timeframe']

    data = manager.load_one_instrument_in_interval(market = instruments['Market'], 
                                                active = instruments['Active'], 
                                                timeframe = instruments['Timeframe'],
                                                name = instruments['Name'],
                                                start = instruments['Start'], 
                                                end = instruments['End'])
    
elif params['instruments_metainfo']['type'] == 'folder':
    instruments = params['instruments']

    timeframe = instruments['Timeframe']

    data = manager.load_all_instrument_in_interval(market = instruments['Market'], 
                                                   active = instruments['Active'], 
                                                   timeframe = instruments['Timeframe'], 
                                                   start = instruments['Start'], 
                                                   end = instruments['End'])

    
    instrument_names = data.columns.get_level_values(0).unique().tolist()

elif params['instruments_metainfo']['type'] == 'dataset':
    instruments = params['instruments']

    timeframe = instruments['Timeframe']

    data = manager.load_dataset(dataset_name = instruments['dataset_name'])
    
    instrument_names = data.columns.get_level_values(0).unique().tolist()

initial_balance = 100 #начальный баланс
data = data.copy()
data['current_state'] = [State(initial_balance) for x in range(len(data))] 

#Определяем стратегию
strategy_info = params['info']

file_path = strategy_info['path']
class_name = strategy_info['name']

spec = importlib.util.spec_from_file_location("my_module", file_path)
module = importlib.util.module_from_spec(spec)
sys.modules["my_module"] = module
spec.loader.exec_module(module)

MyClass = getattr(module, class_name)

known_keys = {'Market','Active','Timeframe','Name','Start','End','commissions','slippage','name','path'}

strategy_params = params['strategy']
strategy_kwargs = {k: v for k, v in strategy_params.items() if k not in known_keys}
strategy_kwargs['main_logger_name'] = logger_name

strategy = MyClass(**strategy_kwargs)

#Определяем брокера
brokers_info = params['brokers']

broker = DemoBroker(commissions=brokers_info['commissions'],
                     slippage=brokers_info['slippage'],
                       main_logger_name=logger_name) 

# Узнаем сколько надо для стратегии на разогрев
min_length = strategy.min_data_length

# Начинаем главный цикл
logger.debug('Начинаю цикл по свечам')

for i in range(min_length, len(data)):
    logger.debug('New bar!')

    history = data[:i+1]
    current_state = data['current_state'].iloc[i-1]
    last_row = data.iloc[i]

    new_state = broker.mark_to_market(current_state=current_state,
                                        last_row=last_row)

    logger.debug('Стратегия принимает решение')
    response = strategy.make_decision(history)
    logger.debug(f'Стратегия вернула {type(response)}')

    logger.debug('Брокер обрабатывает решение стратегии')
    new_state = broker.check_response(current_state=new_state,
                                       response=response,
                                       last_row=last_row)

    logger.debug('Брокер обрабатывает очередь ордеров')
    new_state = broker.process_pending_orders(current_state=new_state,
                                                last_row=last_row)
    
    logger.debug(f'Баланс после действий ордера: {new_state.balance}')
    logger.debug(f'Маржа после действий ордера: {new_state.margin}')
    logger.debug(f'Позиций: {len(new_state.positions)}')
    logger.debug(f'Закрепленных ордеров: {len(new_state.pending_orders)}')

    data.iloc[i, data.columns.get_loc('current_state')] = new_state

    if args.logs:
        current_line = create_logs(response=response,
                                    new_state=new_state,
                                    datetime=data.index[i].isoformat())
        logs.append(current_line)

    logger.debug('end of processing bar')

risk_free_rate = 0
    
def calculate_metrics(states):
    if not states:
        return {
            "total_return": 0,
            "sharp_ratio": 0,
            "max_drawdown": 0
        }
    
    balances = [state.balance for state in states]
    
    initial_balance = balances[0] if balances else 1
    final_balance = balances[-1] if balances else 1

    # diff in percentage
    total_return = final_balance / initial_balance  - 1
    
    max_drawdown = 0
    peak = balances[0] if balances else 1
    
    for balance in balances:
        if balance > peak:
            peak = balance
        drawdown = (peak - balance) / peak if peak > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    returns = []
    for i in range(1, len(balances)):
        if balances[i-1] != 0:
            daily_return = (balances[i] - balances[i-1]) / balances[i-1]
            returns.append(daily_return)

    # sharp calculation
    if returns:
        if timeframe.endswith("d"):
            periods_per_year = 252
        elif timeframe.endswith("w"):
            periods_per_year = 52
        else:
            raise ValueError(f"Not comleted sharp part for {timeframe}!")

        periodic_rf = (1 + risk_free_rate) ** (1 / periods_per_year) - 1
        
        avg_excess_return = sum(r - periodic_rf for r in returns) / len(returns)
        
        avg_raw_return = sum(returns) / len(returns)
        variance = sum((r - avg_raw_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5

        if std_dev > 0:
            annualized_sharpe = (avg_excess_return / std_dev) * (periods_per_year ** 0.5)
        else:
            annualized_sharpe = 0
    else:
        annualized_sharpe  = 0

    # VaR and CVaR calculation
    # change it if you want not 95 cvar
    percentile  = 0.05

    if returns:
        # Calculate VaR
        sorted_returns = sorted(returns)
        var_95_index = max(1, int(percentile * len(sorted_returns)))
        var_95 = sorted_returns[var_95_index]
        
        # CVaR: Average of the worst 5% of returns
        cvar_95 = sum(sorted_returns[:var_95_index]) / var_95_index if var_95_index > 0 else 0
        
    result = {
        "total_return": total_return,
        "sharp_ratio": annualized_sharpe ,
        "max_drawdown": max_drawdown,
        "var_95": var_95,
        "cvar_95": cvar_95
    }

    return result

result = calculate_metrics(data['current_state'].iloc[min_length:].to_list())

if args.logs:
    print('<----Завершаем логгирование',file = sys.stderr, end = '')
    # logs = pd.DataFrame(logs)
    result['logs'] = logs

print(json.dumps(result, default=str))