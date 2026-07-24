import subprocess
import json
import sys
import argparse
import csv
from datetime import datetime

import yaml
import matplotlib.pyplot as plt
import pandas as pd

CONFIG = 'config_single_run_engine.yaml'

def load_config(config_path: str) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config


def run_engine(config: dict) -> None:

    # Формируем словарь для передачи в Engine
    all_params = {
        'instruments': config['instruments'],
        'brokers': config['brokers'],
        'strategy': config['strategy'],
        'info': config['strategy_info']
    }

    # Команда запуска
    command = [
        sys.executable,
        'core/Engine.py',
        '--params', json.dumps(all_params),
        '--logs'
    ]


    result = subprocess.run(command, capture_output=True, text=True)

    # Отладка
    print("=== DEBUG ===")
    print("Return code:", result.returncode)
    print("STDOUT:", repr(result.stdout))
    print("STDERR:", repr(result.stderr))
    print("=== END DEBUG ===")

    if result.returncode != 0:
        print("Engine завершился с ошибкой. Выход.")
        return

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON из stdout Engine: {e}")
        return

    logs = output.get('logs', [])
    if not logs:
        print("Нет данных логов.")
        return

    trades = []
    open_trades = {}  # instrument -> trade_info

    for entry in logs:
        dt = entry['datetime']
        current_positions = entry['positions']  # dict {instr: [pos_dict, ...]}
        balance = entry['balance']

        instruments_with_pos = set(current_positions.keys())

        # Открытие новых позиций
        for instr in instruments_with_pos:
            pos_list = current_positions[instr]
            if pos_list:  # есть позиция
                if instr not in open_trades:
                    pos = pos_list[0]
                    open_trades[instr] = {
                        'instrument': instr,
                        'open_time': dt,
                        'direction': pos['direction'],
                        'volume': pos['volume'],
                        'entry_price': pos['entry_price'],
                        'take_profit': pos['take_profit'],
                        'stop_loss': pos['stop_loss'],
                        'open_balance': balance
                    }
            else:
                # Позиции нет – закрываем, если была открыта
                if instr in open_trades:
                    trade = open_trades.pop(instr)
                    trade['close_time'] = dt
                    trade['pnl'] = balance - trade['open_balance']
                    trades.append(trade)

        # Закрытие позиций, которых больше нет в current_positions
        for instr in list(open_trades.keys()):
            if instr not in instruments_with_pos:
                trade = open_trades.pop(instr)
                trade['close_time'] = dt
                trade['pnl'] = balance - trade['open_balance']
                trades.append(trade)

    # Незакрытые на конец
    for instr, trade in open_trades.items():
        trade['close_time'] = None
        trade['pnl'] = None
        trades.append(trade)

    # --- Построение графика ---
    dates = pd.to_datetime([entry['datetime'] for entry in logs])
    balances = pd.Series([entry['balance'] for entry in logs], index=dates)
    margins = pd.Series([entry['margin'] for entry in logs], index=dates)

    plt.figure(figsize=(12, 6))
    plt.plot(balances.index, balances.values, color='red', linewidth=1.2, label='Balance')
    plt.plot(margins.index, margins.values, color='blue', linewidth=1.2, label='Margin')
    plt.title('Equity Curve')
    plt.legend(loc='upper left')
    plt.gcf().autofmt_xdate()
    plt.tight_layout()

    # Сохранение графика
    equity_plot = config.get('output', {}).get('equity_plot', 'equity.png')
    plt.savefig(equity_plot, dpi=150)
    plt.show()

    # --- Сохранение сделок в CSV ---
    trades_csv = config.get('output', {}).get('trades_csv', 'trades_log.csv')
    with open(trades_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['instrument', 'open_time', 'direction', 'volume', 'entry_price',
                      'take_profit', 'stop_loss', 'close_time', 'pnl', 'open_balance']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trades)

    print(f"Записано {len(trades)} сделок в {trades_csv}")
    print(f"График сохранён как {equity_plot}")


def main():
    parser = argparse.ArgumentParser(description="Single run of trading engine")
    parser.add_argument('--config', type=str, default='configs/run_config.yaml',
                        help='Path to YAML configuration file')
    args = parser.parse_args()

 
    config = load_config(CONFIG)
    run_engine(config)

if __name__ == "__main__":
    main()