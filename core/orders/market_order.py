from core.orders.order import Order
from core.orders.enums import OrderType


class MarketOrder(Order):
    def __init__(self, symbol, side, quantity, take_profit=None, stop_loss=None):
        super().__init__(symbol, side, quantity, OrderType.MARKET,
                          take_profit=take_profit, stop_loss=stop_loss)