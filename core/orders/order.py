from uuid import uuid4
from datetime import datetime

from core.orders.enums import Side, OrderStatus, OrderType


class Order:
    def __init__(self, symbol, side, volume, order_type,
                 take_profit=None, stop_loss=None):
        if not isinstance(side, Side):
            raise ValueError(f"side must be Side, got {side!r}")
        if quantity <= 0:
            raise ValueError("quantity must be positive")

        self.id = str(uuid4())
        self.symbol = symbol
        self.side = side
        self.volume = volume
        self.order_type = order_type
        self.take_profit = take_profit
        self.stop_loss = stop_loss

        self.status = OrderStatus.NEW
        self.created_at = datetime.now()

        self.filled_price = None
        self.filled_quantity = 0
        self.filled_at = None

    def fill(self, price, volume=None):
        if self.status != OrderStatus.NEW:
            raise ValueError(f"cannot fill order in status {self.status}")
        self.filled_price = price
        self.filled_volume = volume or self.volume
        self.filled_at = datetime.now()
        self.status = OrderStatus.FILLED

    def cancel(self):
        if self.status != OrderStatus.NEW:
            raise ValueError(f"cannot cancel order in status {self.status}")
        self.status = OrderStatus.CANCELLED

    def reject(self, reason=None):
        if self.status != OrderStatus.NEW:
            raise ValueError(f"cannot reject order in status {self.status}")
        self.status = OrderStatus.REJECTED
        self.reject_reason = reason