class Response:
    def __init__(self, direction,volume,entry_price):
        if direction not in [-1,0,1]:
            SyntaxWarning("incorrect direction")
        self.direction = direction
        self.volume = volume
        self.entry_price = entry_price

    def get_direction(self):
        return self.direction
        
# a = Response(1)

# print(a.get_direction())