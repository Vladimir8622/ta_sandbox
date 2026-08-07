import pandas as pd
from pathlib import Path
import os, sys

class Data_manager:
    def __init__(self):
        pass             

    def load_instrument(self, market, active, timeframe, name, start, end):
        file_path = Path(f"data/{market}/{active}/{timeframe}/{name}.csv")
        df = pd.read_csv(file_path)
        df["begin"] = pd.to_datetime(df["begin"])

        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)

        mask = (df["begin"] >= start_dt) & (df["begin"] <= end_dt)
        df_filtered = df.loc[mask]

        return df_filtered

    def load_all_instrument_in_interval(self, market, active, timeframe, start, end):

        # Не реалистична, тк откидывает условных банкротов и инструменты что перестали торговать

        folder = Path(f"data/{market}/{active}/{timeframe}")

        data = []

        for name in os.listdir(folder):
            if name.endswith('.csv'):
                Name = name.replace('.csv','')
            else:
                raise ValueError('В папке с данными что-то инородное')
            file_path = Path(f"data/{market}/{active}/{timeframe}/{Name}.csv")
            df = pd.read_csv(file_path)
            df["begin"] = pd.to_datetime(df["begin"])

            start_dt = pd.to_datetime(start)
            end_dt = pd.to_datetime(end)

            mask = (df["begin"] >= start_dt) & (df["begin"] <= end_dt)
            df_filtered = df.loc[mask]

            if df_filtered['close'].isnull().mean() > 0.1:
                continue

            if pd.isna(df_filtered['close'].iloc[0]):
                continue

            if not df_filtered.empty:
                df_filtered = df_filtered.set_index('begin')  
                multi_columns = pd.MultiIndex.from_product([[Name], df_filtered.columns])
                df_filtered.columns = multi_columns
                
                data.append(df_filtered)
        
        data = pd.concat(data, axis=1)
        data = data.sort_index(axis=1)

        return data