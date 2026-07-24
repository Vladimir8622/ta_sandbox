from enum import Enum, auto

class Side(Enum):

    BUY = auto()

    SELL = auto()

class OrderStatus(Enum):

    NEW = auto()

    FILLED = auto()

    CANCELLED = auto()

    REJECTED = auto()