from uuid import uuid4

class Lot:
    def __init__(self, amount, volume):
        self.id = str(uuid4())
        self.amount = amount   
        self.volume = volume   

    def copy(self):
        new_lot = Lot(self.amount, self.volume)
        new_lot.id = self.id
        return new_lot


class Position:
    def __init__(self, direction, volume, entry_price):
        self.id = str(uuid4())
        self.entry_price = entry_price
        self.direction = direction
        self.amount = volume / entry_price
        self.volume = volume
        self.locked_volume = volume
        self.last_mark_price = entry_price
        self.lots = []   # список Lot — только для независимых SL/TP, на margin/PnL не влияет

    def add(self, extra_volume, price):
        extra_amount = extra_volume / price
        self.amount += extra_amount
        self.volume += extra_volume
        self.locked_volume += extra_volume
        self.last_mark_price = price

    def reduce(self, close_amount):
        fraction = close_amount / self.amount
        realized = self.locked_volume * fraction
        self.amount -= close_amount
        self.volume -= self.volume * fraction
        self.locked_volume -= realized
        return realized

    def add_lot(self, volume, price):
        lot = Lot(amount=volume / price, volume=volume)
        self.lots.append(lot)
        return lot

    def reduce_lots_fifo(self, close_amount):
        """Сокращает лоты по FIFO. Возвращает список затронутых (изменённых или закрытых) лотов."""
        remaining = close_amount
        touched = []
        for lot in list(self.lots):
            if remaining <= 1e-12:
                break
            take = min(lot.amount, remaining)
            fraction = take / lot.amount
            lot.amount -= take
            lot.volume -= lot.volume * fraction
            remaining -= take
            touched.append(lot)
            if lot.amount <= 1e-9:
                self.lots.remove(lot)
        return touched

    def copy(self):
        new_pos = Position(direction=self.direction, volume=self.volume, entry_price=self.entry_price)
        new_pos.id = self.id
        new_pos.amount = self.amount
        new_pos.locked_volume = self.locked_volume
        new_pos.last_mark_price = self.last_mark_price
        new_pos.lots = [lot.copy() for lot in self.lots]
        return new_pos