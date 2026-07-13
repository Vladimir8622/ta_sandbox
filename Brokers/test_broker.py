from Brokers.Basic_Broker import Basic_Broker
from Position import Position
from Responses.Wait import Wait

class test_broker(Basic_Broker):
    def __init__(self, commissions, slippage):
        self.commissions = commissions
        self.slippage = slippage

    def check_response(self,current_state,response):
        new_state = current_state.copy()
        if current_state.positions == []:
            if type(response) != type(Wait()):
                if response.direction == 1:
                    position = Position(1,response.volume,response.entry_price,take_profit =  response.take_profit,stop_loss =  response.stop_loss)
                    new_state.balance -= response.volume * (1 + self.commissions + self.slippage)
                    new_state.positions.append(position)
                elif response.direction == -1:
                    position = Position(-1,response.volume,response.entry_price,take_profit = response.take_profit, stop_loss = response.stop_loss)
                    new_state.balance -= response.volume * (1 + self.commissions + self.slippage)
                    new_state.positions.append(position)
                else:
                    raise ValueError('Неправильно заданый ответ стратегии')
            else:
                pass

        return new_state
    def check_position(self, current_state, data):
        new_state = current_state.copy()
        last_price = data['close'].to_list()[-1]
        positions = current_state.positions
        for position in positions[:]:
            current_direction = position.direction
            stop_loss = position.stop_loss
            take_profit = position.take_profit
            if current_direction == 1:
                if last_price < stop_loss or last_price > take_profit:
                    positions.remove(position) 
                    new_state.balance += position.amount * last_price * (1 - self.commissions - self.slippage)
            elif current_direction == -1:
                if last_price > stop_loss or last_price < take_profit:
                    positions.remove(position) 
                    new_state.balance += position.amount * last_price * (1 - self.commissions - self.slippage)
            else: 
                pass
        new_state.positions = positions
        return new_state