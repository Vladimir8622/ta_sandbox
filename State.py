class State:
    def __init__(self,balance = 1):
        self.balance = balance
        self.positions = []
    
    def copy(self):
        new_state = State(balance=self.balance)
        
        new_state.positions = [pos.copy() for pos in self.positions]

        return new_state