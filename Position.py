class Position:
    def __init__(self,id, entry_price,direction,volume,stop_loss,take_profit):
        self.id = id
        self.entry_price = entry_price
        self.direction = direction
        self.volume = volume
        self.stop_loss = stop_loss
        self.take_profit = take_profit