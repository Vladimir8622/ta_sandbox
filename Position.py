class Position:
    '''
    amount - количество штук.
    '''
    def __init__(self,direction,volume, entry_price,take_profit, stop_loss):
        self.entry_price = entry_price
        self.direction = direction
        self.volume = volume
        self.amount = volume/entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit

    def copy(self):
        new_pos = Position(
            direction=self.direction,
            volume = self.volume,
            entry_price = self.entry_price,
            take_profit = self.take_profit,
            stop_loss = self.stop_loss
        )
        return new_pos