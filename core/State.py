class State:
    def __init__(self,balance = 100):
        self.balance = balance
        self.positions = {}
    
    def copy(self):
        new_state = State(balance=self.balance)
        
        new_state.positions = {
            instr: [pos.copy() for pos in pos_list]
            for instr, pos_list in self.positions.items()
        }

        return new_state