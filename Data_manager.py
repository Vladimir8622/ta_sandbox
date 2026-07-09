import pandas as pd
from pathlib import Path

class Data_manager:
    def __init__(self, market, active, timeframe, name, start, end):
        pass             

    def get_data(self, market, active, timeframe, name, start, end):
        file_path = Path(f"data/{market}/{active}/{timeframe}/{name}.csv")
        df = pd.read_csv(file_path)
        df["begin"] = pd.to_datetime(df["begin"])

        start_dt = pd.to_datetime(self.start)
        end_dt = pd.to_datetime(self.end)

        mask = (df["begin"] >= start_dt) & (df["begin"] <= end_dt)
        df_filtered = df.loc[mask]

        return df_filtered
    

