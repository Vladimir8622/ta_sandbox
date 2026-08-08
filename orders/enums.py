from enum import Enum, auto

class Side(Enum):
    BUY = auto()
    SELL = auto()

class OrderType(Enum):
    MARKET = auto()
    LIMIT = auto()
    STOP_LOSS = auto()
    TAKE_PROFIT = auto()

class OrderStatus(Enum):
    PENDING = auto()
    FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()
 