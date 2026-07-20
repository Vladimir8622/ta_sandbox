import data_management.Data_manager as dm
from Brokers.test_broker import test_broker
from Responses.Open_Position import Open_Position
from Responses.Wait import Wait
from State import State
import argparse
import json
import pandas as pd
import sys
import importlib.util

def create_logs(response,new_state,datetime):
    # 1. Преобразуем решения (response) в словарь решений
    decisions_dict = {}
    for instrument, decision in response.items():
        if isinstance(decision, Wait):
            decisions_dict[instrument] = {'type': 'Wait'}
        else:
            decisions_dict[instrument] = {
                'type': 'Open_Position',
                'direction': decision.direction,
                'volume': decision.volume,
                'entry_price': decision.entry_price,
                'take_profit': decision.take_profit,
                'stop_loss': decision.stop_loss
            }
    
    # 2. Преобразуем позиции (new_state.positions) в словарь списков словарей
    positions_dict = {}
    for instrument, pos_list in new_state.positions.items():
        positions_dict[instrument] = []
        for pos in pos_list:
            positions_dict[instrument].append({
                'direction': pos.direction,
                'volume': pos.volume,
                'entry_price': pos.entry_price,
                'take_profit': pos.take_profit,
                'stop_loss': pos.stop_loss,
                'amount': pos.amount
            })
    
    # 3. Формируем запись лога
    current_line = {
        'datetime': datetime,  # сохраняем как строку для JSON
        'balance': new_state.balance,
        'decisions': decisions_dict,   # словарь решений по инструментам
        'positions': positions_dict    # словарь позиций по инструментам
    }
    return current_line

parser = argparse.ArgumentParser()
parser.add_argument('--params', type=str, required=True)
parser.add_argument('--logs', action='store_true')
args = parser.parse_args()
params = json.loads(args.params)

# Включаем логгирование для проверку результатов оптимизации
if args.logs:
    print('Переходим в режим логгирования',file=sys.stderr)
    logs = []

#Загрузка даты
manager = dm.Data_manager()
data = []

for instrument in params['instruments']:
    Market = instrument['Market']
    Active = instrument['Active']
    Timeframe = instrument['Timeframe']
    Name = instrument['Name']
    Start = instrument['Start']
    End = instrument['End']

    df = manager.get_data(Market, Active, Timeframe, Name, Start, End)

    df = df.set_index('begin')  
    
    multi_columns = pd.MultiIndex.from_product([[Name], df.columns])
    df.columns = multi_columns
    
    data.append(df)

data = pd.concat(data, axis=1)

data = data.sort_index(axis=1)
instrument_names = [instr['Name'] for instr in params['instruments']]
close_cols = [(name, 'close') for name in instrument_names]

data = data.dropna(subset=close_cols)

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

strategy = MyClass(**strategy_kwargs)

#Определяем брокера
brokers_info = params['brokers']

commissions = brokers_info['commissions']
slippage = brokers_info['slippage']
broker = test_broker(commissions=commissions, slippage=slippage)

<<<<<<< HEAD
# ??
States = []
initial_balance = 100 #начальный баланс
data['current_state'] = [State(initial_balance) for x in range(len(data))] 
=======

data['current_state'] = [State(1) for x in range(len(data))] 
>>>>>>> ff4237bfc90bbf37321c306d05fae23730cfb2c2

# Узнаем сколько надо для стратегии на разогрев

min_length = strategy.get_min_data_length()

for i in range(min_length, len(data)):
    history = data[:i+1]

    response = strategy.make_decision(history)

    current_state = data['current_state'].iloc[i-1]

    new_state = broker.check_response(current_state, response)

    print('new_state after check_response',file=sys.stderr)
    print(new_state.balance,file=sys.stderr)

    new_state = broker.check_position(new_state, data[:i+1])

    print('new_state after check position',file=sys.stderr)
    print(new_state.balance,file=sys.stderr)

    data.iloc[i, data.columns.get_loc('current_state')] = new_state

    if args.logs:
        current_line = create_logs(response = response,
                                   new_state = new_state,
                                   datetime = data.index[i].isoformat())
        logs.append(current_line)


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
    total_return = final_balance / initial_balance  
    
    max_drawdown = 0
    peak = balances[0] if balances else 1
    
    for balance in balances:
        if balance > peak:
            peak = balance
        drawdown = (peak - balance) / peak * 100 if peak > 0 else 0
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    returns = []
    for i in range(1, len(balances)):
        if balances[i-1] != 0:
            daily_return = (balances[i] - balances[i-1]) / balances[i-1]
            returns.append(daily_return)
    
    if returns:
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5

        if std_dev > 0:
            sharp_ratio = (avg_return / std_dev) 
        else:
            sharp_ratio = 0
    else:
        sharp_ratio = 0
    
    result = {
        "total_return": total_return,
        "sharp_ratio": sharp_ratio,
        "max_drawdown": max_drawdown
    }

    return result

result = calculate_metrics(data['current_state'].iloc[min_length:].to_list())

if args.logs:
    # logs = pd.DataFrame(logs)
    result['logs'] = logs

print(json.dumps(result, default=str))