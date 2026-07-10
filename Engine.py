import data_management.Data_manager as dm
from Strategies.MA_cross import MA_cross 
from Brokers.test_broker import test_broker
from State import State
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument('--params', type=str, required=True)
args = parser.parse_args()
params = json.loads(args.params)

#Загрузка даты
Market = params['Market']
Active = params['Active']
Timeframe = params['Timeframe']
Name = params['Name']
Start = params['Start']
End = params['End']

manager = dm.Data_manager()
data = manager.get_data(Market, Active, Timeframe, Name, Start, End)

#Определяем стратегию
import importlib.util
import sys

file_path = params['path']
class_name = params['name']

spec = importlib.util.spec_from_file_location("my_module", file_path)
module = importlib.util.module_from_spec(spec)
sys.modules["my_module"] = module
spec.loader.exec_module(module)

MyClass = getattr(module, class_name)

known_keys = {'Market','Active','Timeframe','Name','Start','End','commissions','slippage','name','path'}
strategy_kwargs = {k: v for k, v in params.items() if k not in known_keys}

strategy = MyClass(**strategy_kwargs)

#Определяем брокера
commissions = params['commissions']
slippage = params['slippage']
broker = test_broker(commissions=commissions, slippage=slippage)

States = []
data['current_state'] = [State()]* len(data)  

# Узнаем сколько надо для стратегии на разогрев

min_length = strategy.get_min_data_length()

for i in range(min_length, len(data)):
    response = strategy.make_decision(data[:i+1])
    current_state = data['current_state'].iloc[i-1]

    new_state = broker.check_response(current_state, response)
    new_state = broker.check_position(new_state, data[:i+1])
    data.loc[i, 'current_state'] = new_state
    States.append(new_state)
    
    print('new state')
    print(new_state.balance)
    print(new_state.positions)


metrics = {
    "total_return": 12,
    "sharp_ratio": 32,
    "max_drawdown": 1
}

print(json.dumps(metrics))