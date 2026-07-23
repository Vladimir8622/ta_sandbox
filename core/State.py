class State:
    def __init__(self, margin=100):
        self.margin = margin
        self.positions = {}

    @property
    def balance(self):
        locked = sum(pos.locked_amount for pos_list in self.positions.values() for pos in pos_list)
        return self.margin + locked

    def copy(self):
        new_state = State(margin=self.margin)
        new_state.positions = {
            instr: [pos.copy() for pos in pos_list]
            for instr, pos_list in self.positions.items()
        }
        return new_state