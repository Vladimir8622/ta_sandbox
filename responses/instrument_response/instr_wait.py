from responses.basic_response import Response

class instr_Wait(Response):
    def __init__(self, period = 1):
        self.period = period