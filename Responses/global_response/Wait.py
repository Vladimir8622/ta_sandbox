from responses.Basic_Response import Response

class Wait(Response):
    def __init__(self, period = 1):
        self.period = period