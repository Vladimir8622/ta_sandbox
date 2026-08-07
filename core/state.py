class State:
    def __init__(self, margin=100):
        self.margin = margin
        self.positions = {}
        self.pending_orders = []

    @property
    def balance(self):
        locked = sum(pos.locked_volume for pos_list in self.positions.values() for pos in pos_list)
        return self.margin + locked

    # def merge_position(self):
    #     for name, positions in self.positions.items():
    #         for position in positions:



    def copy(self):
        new_state = State(margin=self.margin)
        new_state.positions = {
            instr: [pos.copy() for pos in pos_list]
            for instr, pos_list in self.positions.items()
        }
        new_state.pending_orders = [order.copy() for order in self.pending_orders]

        return new_state