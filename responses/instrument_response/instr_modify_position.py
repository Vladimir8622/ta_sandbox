
from responses.basic_response import Response

class Modify_Position(Response):
    def __init__(self, direction, new_volume, entry_price, take_profit, stop_loss):
        if direction not in [-1,0,1]:
            SyntaxWarning("incorrect direction")
        self.direction = direction
        self.new_volume = new_volume
        self.entry_price = entry_price
        self.take_profit = take_profit
        self.stop_loss = stop_loss