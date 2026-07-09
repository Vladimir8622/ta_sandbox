import Data_manager as dm

param = 0

manager = dm.Data_manager()
data = manager.get_data()

strategy = Strategy

broker = frbwrybwt

states = []

for i in range(begin, end):
    response = strategy.make(data[:i])
    new_state = broker.check_response
    states.append(new_state)

# analysis