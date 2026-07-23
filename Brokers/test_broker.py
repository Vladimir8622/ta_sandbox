from Brokers.Basic_Broker import Basic_Broker
from core.Position import Position
from responses.global_response.Wait import Wait
from responses.instrument_response.instr_wait import instr_Wait
from responses.global_response.Close_all import Close_all
from responses.global_response.Mixed_response import Mixed_response
import logging

class test_broker(Basic_Broker):
    def __init__(self, commissions, slippage, main_logger_name):
        self.commissions = commissions
        self.slippage = slippage

        self.logger = logging.getLogger(main_logger_name + '.' + __name__ + '.' + self.__class__.__name__)

    def _log_state(self,message,state):
        # Строчка ниже просто не дает считать контент сообщений в случае режима info и выше
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(message)
            self.logger.debug(f'Баланс : {state.balance}.')
            self.logger.debug(f'Количество позиций: {sum(map(len, state.positions.values()))},')
            self.logger.debug(f'из которых уникальных инструментов: {len(state.positions)}.')

    def check_response(self,current_state,response,last_row):
        new_state = current_state.copy()
        self._log_state('Перед обработкой запроса.',new_state)

        if isinstance(response, Wait):
            self.logger.debug('Получил wait')
            self._log_state('После обработки запроса.',new_state)
            self.logger.debug('Выхожу из check_response')
            return new_state
        
        if isinstance(response, Close_all):
            self.logger.debug('Получил close all')

            for instrument, decision in current_state.positions.items():
                last_price = last_row[(instrument, 'close')]
                if instrument in new_state.positions:
                    positions = new_state.positions[instrument]
                else:
                    positions = []

                for position in positions[:]:
                    positions.remove(position) 
                    new_state.balance += position.amount * last_price*(1 - self.commissions - self.slippage)

                new_state.positions[instrument] = positions
                if not new_state.positions[instrument]: del new_state.positions[instrument]

            self._log_state('После обработки запроса.',new_state)
            self.logger.debug('Выхожу из check_response')
            return new_state
        
        if isinstance(response, Mixed_response):
            self.logger.debug('Получил Mixed response')

            for instrument, decision in response.positions.items():

                pos_list = new_state.positions.get(instrument, [])

                if type(decision) == type(instr_Wait()):
                    continue

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
            self._log_state('После обработки запроса.',new_state)
            self.logger.debug('Выхожу из check_response')
            return new_state

        raise ValueError('up to this moment every response must be processed')
    
    def check_position(self, current_state, data):
        new_state = current_state.copy()
        self.logger.debug('Зашел в check_position')

        comparasing = False

        for instrument, positions in new_state.positions.items():

            last_price = data[instrument]['close'].to_list()[-1]
            positions = positions

            for position in positions[:]:
                current_direction = position.direction
                stop_loss = position.stop_loss
                take_profit = position.take_profit
                if current_direction == 1:
                    if last_price < stop_loss or last_price > take_profit:
                        self.logger.debug(f'Удаляю позицию из {instrument}')
                        comparasing = True

                        positions.remove(position) 
                        new_state.balance += position.amount * last_price*(1 - self.commissions - self.slippage)
                elif current_direction == -1:
                    if last_price > stop_loss or last_price < take_profit:
                        self.logger.debug(f'Удаляю позицию из {instrument}')
                        comparasing = True

                        positions.remove(position) 
                        new_state.balance += position.amount * last_price*(1 - self.commissions -  self.slippage)
                else: 
                    pass

            new_state.positions[instrument] = positions

        if comparasing:
            self._log_state('До удаления позиций',current_state)
            self._log_state('После удаления позиций',new_state)

        self.logger.debug('Вышел из check_position')
        return new_state