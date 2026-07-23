
from responses.Basic_Response import Response

class Open_Position(Response):
    def __init__(self, direction, volume, entry_price, take_profit, stop_loss):
        if direction not in [-1,0,1]:
            SyntaxWarning("incorrect direction")
        self.direction = direction
        self.volume = volume
        self.entry_price = entry_price
        self.take_profit = take_profit
        self.stop_loss = stop_loss