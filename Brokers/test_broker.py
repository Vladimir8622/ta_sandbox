from Brokers.Basic_Broker import Basic_Broker
from core.Position import Position
from responses.global_response.Wait import Wait
from responses.instrument_response.instr_wait import instr_Wait
from responses.global_response.Close_all import Close_all
from responses.global_response.Mixed_response import Mixed_response
import logging
from core.orders.enums import OrderType, Side, OrderStatus
from core.orders.market_order import MarketOrder

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
 
    def mark_to_market(self, current_state, last_row):
        new_state = current_state.copy()
        self.logger.debug('Зашел в mark_to_market')
 
        for instrument, positions in new_state.positions.items():
            current_price = last_row[(instrument, 'close')]
            for position in positions:
                pnl_delta = (current_price - position.last_mark_price) * position.amount * position.direction
                position.locked_amount += pnl_delta   
                position.last_mark_price = current_price
 
        self._log_state('После переоценки.', new_state)
        self.logger.debug('Вышел из mark_to_market')
        return new_state

    def _response_to_order(self, instrument, decision):
        self.logger.debug('Зашел в response_to_order')

        # decision — это Open_Position из responses/instrument_response
        side = Side.BUY if decision.direction == 1 else Side.SELL
        self.logger.debug('Вышел из response_to_order')

        return MarketOrder(symbol=instrument,
                            side=side,
                            volume=decision.volume,
                            take_profit=decision.take_profit,
                            stop_loss=decision.stop_loss)

    def execute_order(self, order, last_row):
        self.logger.debug('Зашел в execute_order')

        if order.order_type != OrderType.MARKET:
            raise NotImplementedError(order.order_type)

        price = last_row[(order.symbol, 'close')]
        order.fill(price)

        direction = 1 if order.side == Side.BUY else -1
        self.logger.debug('Вышел из execute_order')

        return Position(direction,
                        volume=order.filled_volume,
                        entry_price=order.filled_price,
                        take_profit=order.take_profit,
                        stop_loss=order.stop_loss)
 
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
                    new_state.margin += position.locked_amount
                    new_state.margin -= position.amount * last_price * (self.commissions + self.slippage)
 
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
 
                    order = self._response_to_order(instrument, decision)
                    position = self.execute_order(order, last_row)
                    
                    new_state.margin -= decision.volume * (1 + self.commissions + self.slippage)
                    pos_list.append(position)
 
                elif decision.direction == -1:
 
                    order = self._response_to_order(instrument, decision)
                    position = self.execute_order(order, last_row)
                    
                    new_state.margin -= decision.volume * (1 + self.commissions + self.slippage)
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
                        new_state.margin += position.locked_amount
                        new_state.margin -= position.amount * last_price * (self.commissions + self.slippage)
                elif current_direction == -1:
                    if last_price > stop_loss or last_price < take_profit:
                        self.logger.debug(f'Удаляю позицию из {instrument}')
                        comparasing = True
 
                        positions.remove(position)
                        new_state.margin += position.locked_amount
                        new_state.margin -= position.amount * last_price * (self.commissions + self.slippage)
                else: 
                    pass
 
            new_state.positions[instrument] = positions
 
        if comparasing:
            self._log_state('До удаления позиций',current_state)
            self._log_state('После удаления позиций',new_state)
 
        self.logger.debug('Вышел из check_position')
        return new_state