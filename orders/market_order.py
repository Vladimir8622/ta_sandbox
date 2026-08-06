from orders.order import Order
from orders.enums import OrderType


class MarketOrder(Order):
    def __init__(self, symbol, side, volume, take_profit=None, stop_loss=None):
        super().__init__(symbol, side, volume, OrderType.MARKET,
                          take_profit=take_profit, stop_loss=stop_loss)