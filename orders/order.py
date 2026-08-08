from uuid import uuid4
from datetime import datetime

from orders.enums import Side, OrderStatus, OrderType


class Order:
    def __init__(self, symbol, side, volume, order_type,
                 take_profit=None, stop_loss=None,
                 limit_price=None, trigger_price=None,
                 linked_position_id=None):
        self.id = str(uuid4())
        self.symbol = symbol
        self.side = side
        self.volume = volume
        self.order_type = order_type

        self.take_profit = take_profit
        self.stop_loss = stop_loss

        self.limit_price = limit_price     
        self.trigger_price = trigger_price  
        self.linked_position_id = linked_position_id  

        self.status = OrderStatus.PENDING
        self.created_at = datetime.now()

        self.filled_price = None
        self.filled_volume = 0
        self.filled_at = None
        self.reject_reason = None

    def is_triggered(self, price):
        if self.order_type == OrderType.MARKET:
            return True

        # if self.order_type == OrderType.LIMIT:
        #     if self.side == Side.BUY:
        #         return price <= self.limit_price
        #     else:
        #         return price >= self.limit_price

        if self.order_type == OrderType.STOP_LOSS:       
            return price <= self.trigger_price
        
        if self.order_type == OrderType.TAKE_PROFIT:
            return price >= self.trigger_price  

        return False

    def fill(self, price, volume=None):
        if self.status != OrderStatus.PENDING:
            raise ValueError(f"cannot fill order in status {self.status}")
        
        self.filled_price = price
        self.filled_volume = volume or self.volume
        self.filled_at = datetime.now()
        self.status = OrderStatus.FILLED

    def cancel(self):
        # if self.status != OrderStatus.PENDING:
        #     raise ValueError(f"cannot cancel order in status {self.status}")
        self.status = OrderStatus.CANCELLED

    # def reject(self, reason=None):
    #     if self.status != OrderStatus.PENDING:
    #         raise ValueError(f"cannot reject order in status {self.status}")
    #     self.status = OrderStatus.REJECTED
    #     self.reject_reason = reason

    def copy(self):
        new_order = Order(
            symbol=self.symbol, side=self.side, volume=self.volume,
            order_type=self.order_type, take_profit=self.take_profit,
            stop_loss=self.stop_loss, limit_price=self.limit_price,
            trigger_price=self.trigger_price,
            linked_position_id=self.linked_position_id)
        new_order.id = self.id
        new_order.status = self.status
        new_order.filled_price = self.filled_price
        new_order.filled_volume = self.filled_volume
        new_order.filled_at = self.filled_at
        new_order.created_at = self.created_at
        return new_order