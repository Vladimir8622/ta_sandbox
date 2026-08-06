from brokers.basic_broker import Basic_Broker
from core.position import Position
from responses.global_response.wait import Wait
from responses.instrument_response.instr_wait import instr_Wait
from responses.global_response.close_all import Close_all
from responses.global_response.mixed_response import Mixed_response
import logging
from orders.enums import OrderType, Side, OrderStatus
from orders.order import Order

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
                position.locked_volume += pnl_delta   
                position.last_mark_price = current_price
 
        self._log_state('После переоценки.', new_state)
        self.logger.debug('Вышел из mark_to_market')
        return new_state

    def _response_to_order(self, instrument, decision):
        side = Side.BUY if decision.direction == 1 else Side.SELL
        return Order(symbol=instrument, side=side, volume=decision.volume,
                     order_type=OrderType.MARKET,
                     take_profit=decision.take_profit,
                     stop_loss=decision.stop_loss)

    
 
    def check_response(self, current_state, response, last_row):
        new_state = current_state.copy()
        self._log_state('Перед обработкой запроса.', new_state)

        if isinstance(response, Wait):
            return new_state

        if isinstance(response, Close_all):
            for instrument, decision in current_state.positions.items():
                last_price = last_row[(instrument, 'close')]
                positions = new_state.positions.get(instrument, [])

                for position in positions[:]:
                    positions.remove(position)
                    new_state.margin += position.locked_volume
                    new_state.margin -= position.amount * last_price * (self.commissions + self.slippage)

                new_state.positions[instrument] = positions
                if not new_state.positions[instrument]:
                    del new_state.positions[instrument]

            for order in new_state.pending_orders:
                if order.status == OrderStatus.PENDING:
                    order.cancel()
            new_state.pending_orders = []
            return new_state

        if isinstance(response, Mixed_response):
            for instrument, decision in response.positions.items():
                pos_list = new_state.positions.get(instrument, [])

                if type(decision) == type(instr_Wait()):
                    continue
                if len(pos_list) > 2:
                    continue

                if decision.direction in (1, -1):
                    order = self._response_to_order(instrument, decision)
                    new_state.pending_orders.append(order)
                else:
                    raise ValueError('Неправильно заданый ответ стратегии')

            self._log_state('После обработки запроса.', new_state)
            return new_state

        raise ValueError('up to this moment every response must be processed')
    
    def _make_exit_orders(self, symbol, position):
        close_side = Side.SELL if position.direction == 1 else Side.BUY
        orders = []
        if position.stop_loss is not None:
            orders.append(Order(symbol=symbol, side=close_side, volume=position.volume,
                                 order_type=OrderType.STOP,          # SL
                                 trigger_price=position.stop_loss,
                                 linked_position_id=position.id))
        if position.take_profit is not None:
            orders.append(Order(symbol=symbol, side=close_side, volume=position.volume,
                                 order_type=OrderType.LIMIT,         # TP
                                 limit_price=position.take_profit,
                                 linked_position_id=position.id))
        return orders

    def _fill_entry(self, state, order, price):
        order.fill(price)
        direction = 1 if order.side == Side.BUY else -1
        position = Position(direction,
                             volume=order.filled_volume,
                             entry_price=order.filled_price,
                             take_profit=order.take_profit,
                             stop_loss=order.stop_loss)

        state.margin -= order.filled_volume * (1 + self.commissions + self.slippage)
        state.positions.setdefault(order.symbol, []).append(position)
        state.pending_orders += self._make_exit_orders(order.symbol, position)

    def _fill_exit(self, state, order, price):
        positions = state.positions.get(order.symbol, [])
        position = next((p for p in positions if p.id == order.linked_position_id), None)

        if position is None:
            order.cancel()   
            return

        order.fill(price)
        positions.remove(position)
        state.margin += position.locked_volume
        state.margin -= position.amount * price * (self.commissions + self.slippage)

        state.positions[order.symbol] = positions
        if not state.positions[order.symbol]:
            del state.positions[order.symbol]

        for other in state.pending_orders:
            if other.linked_position_id == position.id and other.status == OrderStatus.PENDING:
                other.cancel()

    def process_pending_orders(self, current_state, last_row):
        #Вызывать ДО check_respons на каждой итерации
        new_state = current_state.copy()
        still_pending = []

        for order in new_state.pending_orders:
            if order.status != OrderStatus.PENDING:
                continue

            price = last_row[(order.symbol, 'close')]

            if order.is_triggered(price):
                if order.linked_position_id is None:
                    self._fill_entry(new_state, order, price)
                else:
                    self._fill_exit(new_state, order, price)
            else:
                still_pending.append(order)

        new_state.pending_orders = still_pending
        self._log_state('После обработки очереди ордеров.', new_state)
        return new_state
    
    