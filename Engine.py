import data_management.Data_manager as dm
from Strategies.MA_cross import MA_cross 
from Brokers.test_broker import test_broker
from State import State
#Загрузка даты
Market = "MOEX"
Active = "adjusted_stock"
Timeframe = "1d"
Name = "ABIO.MOEX"
Start = "2023-08-18"
End = "2026-07-08"
manager = dm.Data_manager()
data = manager.get_data(Market, Active, Timeframe, Name, Start, End)

#Определяем стратегию
ma_slow = 20
ma_fast = 5
strategy = MA_cross(ma_slow, ma_fast)

#Определяем брокера
broker = test_broker(3*10**(-4), 10**(-5))

States = []
data['current_state'] = [State()]* len(data)  


for i in range(ma_slow+1, len(data)):
    response = strategy.make_decision(data[:i])
    current_state = data['current_state'].iloc[-1]
    new_state = broker.check_response(current_state, response)
    new_state = broker.check_position(current_state, data)
    data.loc[i, 'current_state'] = new_state
    States.append(new_state)
    print(new_state.balance)

