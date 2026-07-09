import data_management.Data_manager as dm
import Strategies.MA_cross
import Broker
import pandas as pd

#Загрузка даты
Market = "MOEX"
Active = "adjusted_stock"
Timeframe = "1d"
Name = "ABIO.MOEX"
Start = 2023-08-18
End = 2026-07-08
manager = dm.Data_manager()
data = manager.get_data(Market, Active, Timeframe, Name, Start, End)

#Определяем стратегию
ma_slow = 200
ma_fast = 50
strategy = Strategies.MA_cross(ma_slow, ma_fast)

#Определяем брокера
broker = Broker(3*10**(-4), 10**(-5))

States = []

for i in range(Start, End):
    response = strategy.make(data[:i])
    current_state = data['current_state']
    new_state = broker.check_response()
    broker.check_position
    states.append(new_state)

# analysis