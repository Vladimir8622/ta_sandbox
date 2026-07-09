class Position:
    def __init__(self,direction,volume, entry_price,take_profit, stop_loss):
        self.entry_price = entry_price
        self.direction = direction
        self.volume = volume
        self.stop_loss = stop_loss
        self.take_profit = take_profit

    def copy(self):
        new_pos = Position(
            self.entry_price,
            self.direction,
            self.volume,
            self.stop_loss,
            self.take_profit
        )