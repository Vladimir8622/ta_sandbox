class Position:
    def __init__(self, direction, volume, entry_price, take_profit, stop_loss):
        self.entry_price = entry_price
        self.direction = direction
        self.volume = volume
        self.amount = volume / entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.locked_volume = volume 
        self.last_mark_price = entry_price 

    def copy(self):
        new_pos = Position(
            direction = self.direction,
            volume = self.volume,
            entry_price = self.entry_price,
            take_profit = self.take_profit,
            stop_loss = self.stop_loss)
        new_pos.locked_volume = self.locked_volume
        new_pos.last_mark_price = self.last_mark_price
        return new_pos