class Position:
    def __init__(self, direction, volume, entry_price, take_profit, stop_loss):
        self.entry_price = entry_price
        self.direction = direction
        self.volume = volume
        self.amount = volume / entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.locked_amount = volume        #заморожено
        self.last_mark_price = entry_price 

    def copy(self):
        new_pos = Position(self.direction, self.volume, self.entry_price, self.take_profit, self.stop_loss)
        new_pos.locked_amount = self.locked_amount
        new_pos.last_mark_price = self.last_mark_price
        return new_pos