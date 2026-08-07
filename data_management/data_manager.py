import pandas as pd
from pathlib import Path
import os, sys
import pyarrow.parquet as pq

class Data_manager:
    def __init__(self):
        pass             

    def load_one_instrument_in_interval(self, market, active, timeframe, name, start, end):
        file_path = Path(f"data/{market}/{active}/{timeframe}/{name}.csv")
        df = pd.read_csv(file_path)
        df["begin"] = pd.to_datetime(df["begin"])

        start_dt = pd.to_datetime(start)
        end_dt = pd.to_datetime(end)

        mask = (df["begin"] >= start_dt) & (df["begin"] <= end_dt)
        df_filtered = df.loc[mask]

        df = df_filtered.set_index('begin')  
            
        multi_columns = pd.MultiIndex.from_product([[name], df.columns])
        df.columns = multi_columns

        data = []
        
        data.append(df)
    
        data = pd.concat(data, axis=1)
        data = data.sort_index(axis=1)

        return data

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

            if df_filtered['close'].isnull().mean() > 0.0:
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

        # чутка брутально, зато гарантирует чистоту данных
        data = data.dropna(axis=1, how='any')

        return data

    def load_dataset(self, dataset_name: str, ffill_nan: bool = True):
        """
            dataset_name (str): имя папки датасета (например, 'moex_adjusted_stock').
            ffill_nan (bool): если True, выполняет forward fill по времени для всех колонок.
        """
        dataset_path = Path(f"data/datasets/{dataset_name}")
        if not dataset_path.exists():
            raise FileNotFoundError(f"Датасет {dataset_name} не найден по пути {dataset_path}")

        parquet_files = sorted(dataset_path.glob("*.parquet"))
        if not parquet_files:
            raise FileNotFoundError(f"В {dataset_path} нет .parquet файлов")

        data_frames = []

        for file_path in parquet_files:
            ticker = file_path.stem  # имя файла без расширения

            # Чтение через pyarrow с memory_map (экономия памяти)
            table = pq.read_table(file_path, memory_map=True)
            df = table.to_pandas()

            # Приводим типы (на всякий случай)
            df['date'] = pd.to_datetime(df['date'])
            df['close'] = pd.to_numeric(df['close'], errors='coerce')

            # Устанавливаем дату как индекс
            df = df.set_index('date')
            # Создаём MultiIndex для колонок: (тикер, 'close')
            df.columns = pd.MultiIndex.from_product([[ticker], df.columns])

            data_frames.append(df)

        if not data_frames:
            raise ValueError("Нет данных в датасете")

        # Объединяем все инструменты по горизонтали (индекс — даты)
        combined = pd.concat(data_frames, axis=1)

        # Сортируем колонки по тикеру для удобства
        combined = combined.sort_index(axis=1)

        # Forward fill по времени, если задан флаг
        if ffill_nan:
            combined = combined.ffill(axis=0)
            # (Опционально) удалить строки, где все колонки NaN
            # combined = combined.dropna(how='all')

        return combined