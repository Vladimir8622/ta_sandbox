from uuid import uuid4

class Position:
    def __init__(self, direction, volume, entry_price):
        self.id = str(uuid4())
        self.entry_price = entry_price   # справочно, в расчётах P&L не участвует
        self.direction = direction
        self.amount = volume / entry_price
        self.volume = volume             # текущая денежная стоимость позиции
        self.locked_volume = volume      # переоценённая стоимость, обновляется в mark_to_market
        self.last_mark_price = entry_price

    def add(self, extra_volume, price):
        """Доливка в ту же сторону."""
        extra_amount = extra_volume / price
        self.amount += extra_amount
        self.volume += extra_volume
        self.locked_volume += extra_volume
        self.last_mark_price = price

    def reduce(self, close_amount):
        """close_amount — в монетах. Возвращает высвобожденные locked_volume (деньги)."""
        fraction = close_amount / self.amount
        realized = self.locked_volume * fraction
        self.amount -= close_amount
        self.volume -= self.volume * fraction
        self.locked_volume -= realized
        return realized

    def copy(self):
        new_pos = Position(direction=self.direction, volume=self.volume, entry_price=self.entry_price)
        new_pos.id = self.id
        new_pos.amount = self.amount
        new_pos.locked_volume = self.locked_volume
        new_pos.last_mark_price = self.last_mark_price
        return new_pos