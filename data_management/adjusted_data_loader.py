import os
import time
import requests
import pandas as pd
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# Параметры загрузки
first_date = "1900-01-01"
last_date  = "2100-01-01"
period = "d"  # дневные данные

def create_robust_session():
    """
    Create a session with robust retry configuration
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    
    # Mount adapter with retry strategy
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=1, pool_maxsize=1)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Configure session with reasonable defaults
    session.headers.update({
        'User-Agent': 'MOEX Data Loader/1.0',
        'Accept': 'application/json',
        'Connection': 'keep-alive'
    })
    
    return session

# 1. Получаем список всех акций на MOEX
session = create_robust_session()
response = session.get("https://api.okama.io/api/namespaces/MOEX", timeout=30)
response.raise_for_status()
data = response.json()
tickers = pd.DataFrame(data)

print(f"Найдено {len(tickers)} инструментов на MOEX")

# Переносим первую строку в названия столбцов
tickers.columns = tickers.iloc[0].tolist()
tickers = tickers[1:].reset_index(drop=True)

# Вильтруем только акции
tickers = tickers[tickers['type'] == 'Common Stock']
names = tickers['symbol'].to_list()
print(f"Найдено акций: {len(names)}")
print(names[:10])  # покажем первые 10


# Создаём папку для сохранения
os.makedirs("data/MOEX/adjusted_stock/1d/", exist_ok=True)

# Загружаем adjusted‑close для каждого тикера
for ticker in names:
    symbol = ticker
    url = f"https://api.okama.io/api/ts/adjusted_close/{symbol}"
    params = {
        "first_date": first_date,
        "last_date":  last_date,
        "period":     period
    }

    try:
        resp = session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        
        # Сохраняем полученный CSV в файл
        file_path = f"data/MOEX/adjusted_stock/1d/{ticker}.csv"
        if os.path.exists(file_path):
            continue
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(resp.text)
        
        print(f"✅ Загружено: {ticker}")
    except Exception as e:
        print(f"❌ Ошибка для {ticker}: {e}")
    
    time.sleep(1)  # пауза, чтобы не перегружать API

print("🎉 Все файлы сохранены в data/MOEX/adjusted_stock/1d/")