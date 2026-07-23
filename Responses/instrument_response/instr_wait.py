from Responses.Basic_Response import Response

class instr_Wait(Response):
    def __init__(self, period = 1):
        self.period = period