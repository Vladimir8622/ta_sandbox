import data_management.Data_manager as dm
from Brokers.test_broker import test_broker
from Responses.Open_Position import Open_Position
from Responses.Wait import Wait
from State import State
import argparse
import json
import pandas as pd
import sys

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

#Определяем стратегию
import importlib.util
import sys

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

# ??
States = []

data['current_state'] = [State(1) for x in range(len(data))] 

# Узнаем сколько надо для стратегии на разогрев

min_length = strategy.get_min_data_length()

for i in range(min_length, len(data)):
    history = data[:i+1]

    response = strategy.make_decision(history)

    current_state = data['current_state'].iloc[i-1]

    new_state = broker.check_response(current_state, response)
    new_state = broker.check_position(new_state, data[:i+1])
    data.iloc[i, data.columns.get_loc('current_state')] = new_state
    States.append(new_state)

    # if args.logs:
    #     # Преобразуем response в словарь
    #     if isinstance(response, Wait):
    #         decision_dict = {'type': 'Wait'}
    #     else:
    #         decision_dict = {
    #             'type': 'Open_Position',
    #             'direction': response.direction,
    #             'volume': response.volume,
    #             'entry_price': response.entry_price,
    #             'take_profit': response.take_profit,
    #             'stop_loss': response.stop_loss
    #         }
    #     # Преобразуем positions в список словарей
    #     positions_list = []
    #     for pos in new_state.positions:
    #         positions_list.append({
    #             'direction': pos.direction,
    #             'volume': pos.volume,
    #             'entry_price': pos.entry_price,
    #             'take_profit': pos.take_profit,
    #             'stop_loss': pos.stop_loss,
    #             'amount': pos.amount
    #         })
    #     current_line = {
    #         'datetime': data.index[i],
    #         'balance': new_state.balance,
    #         'decision': decision_dict,
    #         'positions': positions_list
    #     }
    #     logs.append(current_line)


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
result = calculate_metrics(States)

if args.logs:
    # logs = pd.DataFrame(logs)
    result['logs'] = logs

print(json.dumps(result, default=str))