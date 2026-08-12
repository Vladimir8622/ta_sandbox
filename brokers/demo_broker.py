from brokers.basic_broker import Basic_Broker
from core.position import Position
from responses.global_response.wait import Wait
from responses.instrument_response.instr_wait import instr_Wait
from responses.instrument_response.instr_open_position import Open_Position
from responses.instrument_response.instr_modify_position import Modify_Position
from responses.global_response.close_all import Close_all
from responses.global_response.mixed_response import Mixed_response
import logging
from orders.enums import OrderType, Side, OrderStatus
from orders.order import Order


class DemoBroker(Basic_Broker):
    def __init__(self, commissions, slippage, main_logger_name):
        self.commissions = commissions
        self.slippage = slippage
        self.logger = logging.getLogger(main_logger_name + '.' + __name__ + '.' + self.__class__.__name__)

    def _log_state(self, message, state):
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(message)
            self.logger.debug(f'Баланс : {state.balance}.Маржа : {state.margin}')
            self.logger.debug(f'Позиций: {len(state.positions)}. Закрепленных ордеров: {len(state.pending_orders)}. Ордеров в истории: {len(state.history_orders)}.')

    def mark_to_market(self, current_state, last_row):
        new_state = current_state.copy()
        self.logger.debug('Зашел в mark_to_market')

        for instrument, position in new_state.positions.items():
            current_price = last_row[(instrument, 'close')]
            pnl_delta = (current_price - position.last_mark_price) * position.amount * position.direction
            position.locked_volume += pnl_delta
            position.last_mark_price = current_price

        self._log_state('После переоценки.', new_state)
        self.logger.debug('Вышел из mark_to_market')
        return new_state


    def _make_exit_orders(self, instrument, position, lot, stop_loss, take_profit):
        orders = []
        exit_side = Side.SELL if position.direction == 1 else Side.BUY
        if stop_loss is not None:
            orders.append(Order(symbol=instrument, side=exit_side, volume=lot.volume,
                                order_type=OrderType.STOP_LOSS, trigger_price=stop_loss,
                                linked_lot_id=lot.id))
        if take_profit is not None:
            orders.append(Order(symbol=instrument, side=exit_side, volume=lot.volume,
                                order_type=OrderType.TAKE_PROFIT, trigger_price=take_profit,
                                linked_lot_id=lot.id))
        return orders

    def _sync_linked_orders(self, state, lot):
        for order in state.pending_orders:
            if order.linked_lot_id == lot.id and order.status == OrderStatus.PENDING:
                order.volume = lot.volume

    def _cancel_linked_orders(self, state, lot_id):
        for order in state.pending_orders:
            if order.linked_lot_id == lot_id and order.status == OrderStatus.PENDING:
                order.cancel()

    def _cancel_sibling_exit_order(self, state, order):
        # Закрываем тип связанные ордера
        """OCO — теперь СКОУПЛЕН на конкретный лот, а не на всю позицию."""
        if order.linked_lot_id is None:
            return
        if order.order_type not in (OrderType.STOP_LOSS, OrderType.TAKE_PROFIT):
            return
        for other in state.pending_orders:
            if (other.linked_lot_id == order.linked_lot_id
                    and other.id != order.id
                    and other.status == OrderStatus.PENDING):
                other.cancel()


    def _fill_order(self, state, order, price):
        position = state.positions.get(order.symbol)
        lot = None

        if order.linked_lot_id is not None:
            if position is not None:
                lot = next(
                    (l for l in position.lots if l.id == order.linked_lot_id),
                    None
                )

        order.fill(price)
        self._cancel_sibling_exit_order(state, order)

        instrument = order.symbol
        fill_dir = 1 if order.side == Side.BUY else -1
        fill_volume = order.filled_volume
        commission = fill_volume * (self.commissions + self.slippage)

        if position is None:
            new_position = Position(
                direction=fill_dir,
                volume=fill_volume,
                entry_price=price
            )

            lot = new_position.add_lot(fill_volume, price)
            state.positions[instrument] = new_position
            state.margin -= fill_volume + commission

            state.pending_orders += self._make_exit_orders(
                instrument,
                new_position,
                lot,
                order.stop_loss,
                order.take_profit
            )

        elif position.direction == fill_dir:
            position.add(fill_volume, price)
            lot = position.add_lot(fill_volume, price)
            state.margin -= fill_volume + commission

            state.pending_orders += self._make_exit_orders(
                instrument,
                position,
                lot,
                order.stop_loss,
                order.take_profit
            )

        elif fill_volume < position.volume - 1e-9:

            if order.linked_lot_id is not None:
                if lot is None:
                    order.cancel()
                    return

                # SL/TP закрывает весь конкретный лот
                close_amount = lot.amount

            else:
                # Обычный выход / Modify_Position:
                # volume — деньги, amount — количество инструмента
                close_amount = fill_volume / price

            realized = position.reduce(close_amount)
            touched_lots = position.reduce_lots_fifo(close_amount)

            state.margin += realized - commission

            for lot in touched_lots:
                if lot.amount <= 1e-9:
                    self._cancel_linked_orders(state, lot.id)
                else:
                    self._sync_linked_orders(state, lot)

        elif abs(fill_volume - position.volume) <= 1e-9:
            state.margin += position.locked_volume - commission

            for lot in list(position.lots):
                self._cancel_linked_orders(state, lot.id)

            del state.positions[instrument]

        else:
            remainder = fill_volume - position.volume

            state.margin += position.locked_volume - commission

            for lot in list(position.lots):
                self._cancel_linked_orders(state, lot.id)

            remainder_commission = remainder * (
                self.commissions + self.slippage
            )

            new_position = Position(
                direction=fill_dir,
                volume=remainder,
                entry_price=price
            )

            lot = new_position.add_lot(remainder, price)
            state.positions[instrument] = new_position
            state.margin -= remainder + remainder_commission

            state.pending_orders += self._make_exit_orders(
                instrument,
                new_position,
                lot,
                order.stop_loss,
                order.take_profit
            )

        state.history_orders.append(order)

    def process_pending_orders(self, current_state, last_row):
        self.logger.debug('Зашел в process_pending_orders')
        self._log_state('Перед обработкой очереди ордеров.', current_state)
        new_state = current_state.copy()

        for order in new_state.pending_orders:
            if order.status != OrderStatus.PENDING:
                # А как такие вообще должны сюда попадать?
                # вот и ответ. через связанные id. закрываются заранее
                # raise ValueError(f'Незакрепленный ордер в списке закрепленных. Конкретно {order.status}')
                continue

            price = last_row[(order.symbol, 'close')]
            if order.is_triggered(price):
                self._fill_order(new_state, order, price)
            else:
                # Ордер не задействован
                continue

        new_state.pending_orders = [o for o in new_state.pending_orders if o.status == OrderStatus.PENDING]
        # Почему не тут добавление обработанных ордеров в историю? Получается кажется что в историю сохранются только маркетные и выполненые граничные.

        self.logger.debug('Вышел из process_pending_orders')
        self._log_state('После обработки очереди ордеров.', new_state)
        return new_state

    def check_response(self, current_state, response, last_row):
        new_state = current_state.copy()
        self._log_state('Перед обработкой запроса.', new_state)

        if isinstance(response, Wait):
            self.logger.debug('Получил Wait, вернул без изменений')
            return new_state

        if isinstance(response, Close_all):
            self.logger.debug('Получил Close_all')
            for instrument, position in list(new_state.positions.items()):
                last_price = last_row[(instrument, 'close')]
                commission = position.amount * last_price * (self.commissions + self.slippage)
                new_state.margin += position.locked_volume - commission
                for lot in list(position.lots):
                    self._cancel_linked_orders(new_state, lot.id)
                del new_state.positions[instrument]
            new_state.pending_orders = [o for o in new_state.pending_orders if o.status == OrderStatus.PENDING]
            return new_state

        if isinstance(response, Mixed_response):
            self.logger.debug('Получил Mixed_response')
            for instrument, decision in response.positions.items():

                if isinstance(decision, instr_Wait):
                    continue

                elif isinstance(decision, Open_Position):
                    if decision.direction not in (1, -1):
                        raise ValueError('Неправильно заданый ответ стратегии')
                    
                    side = Side.BUY if decision.direction == 1 else Side.SELL
                    order = Order(symbol=instrument, side=side, volume=decision.volume,
                                  order_type=OrderType.MARKET,
                                  stop_loss=decision.stop_loss, take_profit=decision.take_profit)
                    new_state.pending_orders.append(order)

                elif isinstance(decision, Modify_Position):
                    position = new_state.positions.get(instrument)
                    current_signed = (position.direction * position.volume) if position else 0
                    delta = decision.new_volume - current_signed   
                    if abs(delta) > 1e-9:
                        side = Side.BUY if delta > 0 else Side.SELL
                        order = Order(symbol=instrument, side=side, volume=abs(delta),
                                      order_type=OrderType.MARKET,
                                      stop_loss=decision.stop_loss, take_profit=decision.take_profit)
                        new_state.pending_orders.append(order)
                    else:
                        # Никаких изменений по активу
                        continue

            self._log_state('После обработки запроса.', new_state)
            return new_state

        raise ValueError('up to this moment every response must be processed')