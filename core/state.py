class State:
    def __init__(self, margin=100):
        self.margin = margin
        self.positions = {}       # instrument -> Position (одна на инструмент)
        self.pending_orders = []
        self.history_orders = []

    @property
    def balance(self):
        locked = sum(pos.locked_volume for pos in self.positions.values())
        return self.margin + locked

    def copy(self):
        new_state = State(margin=self.margin)
        new_state.positions = {
            instr: pos.copy() for instr, pos in self.positions.items()
        }
        new_state.pending_orders = [order.copy() for order in self.pending_orders]
        new_state.history_orders = list(self.history_orders)
        return new_state