from Brokers.Basic_Broker import Basic_Broker
import Position

class test_broker(Basic_Broker):
    def __init__(self, commissions, slippage):
        self.commissions = commissions
        self.slippage = slippage

    def check_response(self,current_state,response):
        new_state = current_state.copy()

        if response.get_direction() == 1:
            new_state.balance -= response.volume * (1 + self.commissions + self.slippage)
            position = Position(1)
            new_state.positions.append(position)
        elif response.get_direction() == -1:
            new_state.balance -= response.volume * (1 + self.commissions + self.slippage)
            position = Position(-1)
            new_state.positions.append(position)
        else:
            pass

        return new_state
    def check_position(self, current_state, data):
        new_state = current_state.copy()
        last_price = data['close'].to_list()[-1]
        positions = current_state.postions()
        for position in positions:
            current_direction = current_state.postions(position).direction
            stop_loss = current_state.postions(position).stop_loss
            take_profit = current_state.postions(position).take_profit
            if current_direction == 1:
                if last_price < stop_loss:
                    positions.remove(position) 
                    new_state.balance -= position.volume * (1 + self.commissions + self.slippage)
                elif last_price > take_profit:
                    positions.remove(position) 
                    new_state.balance += position.volume * (1 + self.commissions + self.slippage)
            elif current_direction == -1:
                if last_price > stop_loss:
                    positions.remove(position) 
                    new_state.balance -= position.volume * (1 + self.commissions + self.slippage)
                elif last_price < take_profit:
                    positions.remove(position) 
                    new_state.balance += position.volume * (1 + self.commissions + self.slippage)
            else: 
                pass
        return new_state