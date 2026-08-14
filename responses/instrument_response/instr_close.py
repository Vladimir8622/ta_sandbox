from responses.basic_response import Response

class Close(Response):
    def __init__(self, volume=None, direction=None):
        self.volume = volume
        self.direction = direction