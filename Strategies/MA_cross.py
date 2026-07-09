from Strategies.Basic_Strategy import Basic_Strategy

class MA_cross(Basic_Strategy):
    def __init__(self, long_period,short_period):
        super()
        self.long_period = long_period
        self.short_period = short_period
    
    def make_decision(self, data):
        # calculating MA
        reversed_data = data.iloc[::-1]
        data['long_MA'][0] = data['close'][:self.long_period]
        data['short_MA'][0] = data['close'][:self.short_period]

        data['long_MA'][1] = data['close'][:self.long_period]
        data['short_MA'][1] = data['close'][:self.short_period]

        return 