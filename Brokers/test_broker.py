from Brokers.Basic_Broker import Basic_Broker
from Position import Position
from Responses.Wait import Wait
from Responses.Close_all import Close_all

class test_broker(Basic_Broker):
    def __init__(self, commissions, slippage):
        self.commissions = commissions
        self.slippage = slippage

    def check_response(self,current_state,response,last_row):
        new_state = current_state.copy()

        for instrument, decision in response.items():

            pos_list = new_state.positions.get(instrument, [])

            # Разобраться почему isinstant не работает
            if type(decision) == type(Wait()):
                continue
            if type(decision) == type(Close_all()):
                new_state = current_state.copy()

                for instrument, decision in response.items():
                    last_price = last_row[(instrument, 'close')]
                    if instrument in new_state.positions:
                        positions = new_state.positions[instrument]
                    else:
                        # В случае если инструмента еще не было
                        positions = []

                    for position in positions[:]:
                        positions.remove(position) 
                        new_state.balance += position.amount * last_price*(1 - self.commissions - self.slippage)

                    new_state.positions[instrument] = positions
                    # добавить проверку что массив пуст

                return new_state

            if len(pos_list)>2:
                continue

            if decision.direction == 1:

                position = Position(1,
                                    volume = decision.volume,
                                    entry_price = decision.entry_price,
                                    take_profit =  decision.take_profit,
                                    stop_loss =  decision.stop_loss)
                
                new_state.balance -= decision.volume * (1 + self.commissions + self.slippage)
                pos_list.append(position)

            elif decision.direction == -1:
                position = Position(-1,
                                    volume = decision.volume,
                                    entry_price = decision.entry_price,
                                    take_profit = decision.take_profit,
                                    stop_loss = decision.stop_loss)
                new_state.balance -= decision.volume * (1 + self.commissions + self.slippage)
                pos_list.append(position)
            else:
                raise ValueError('Неправильно заданый ответ стратегии')
            
            new_state.positions[instrument] = pos_list


        return new_state
    

    def check_position(self, current_state, data):
        new_state = current_state.copy()

        for instrument, positions in new_state.positions.items():

            last_price = data[instrument]['close'].to_list()[-1]
            positions = positions

            for position in positions[:]:
                current_direction = position.direction
                stop_loss = position.stop_loss
                take_profit = position.take_profit
                if current_direction == 1:
                    if last_price < stop_loss or last_price > take_profit:
                        positions.remove(position) 
                        new_state.balance += position.amount * last_price*(1 - self.commissions - self.slippage)
                elif current_direction == -1:
                    if last_price > stop_loss or last_price < take_profit:
                        positions.remove(position) 
                        new_state.balance += position.amount * last_price*(1 - self.commissions -  self.slippage)
                else: 
                    pass

            new_state.positions[instrument] = positions
        return new_state