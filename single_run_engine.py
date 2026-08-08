import subprocess
import json
import sys
import argparse
import csv
from datetime import datetime

import yaml
import matplotlib.pyplot as plt
import pandas as pd
import os

def load_config(config_path: str) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def run_engine(config: dict) -> None:

    run_dir = fr"single_run_res\{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    os.makedirs(run_dir, exist_ok=True)

    equity_filename = config.get('output', {}).get('equity_plot', 'equity.png')
    trades_filename = config.get('output', {}).get('trades_csv', 'trades_log.csv')
    orders_filename = config.get('output', {}).get('orders_csv', 'orders_log.csv')
    history_filename = config.get('output', {}).get('history_orders_csv', 'history_orders_log.csv')

    equity_plot_path = os.path.join(run_dir, equity_filename)
    trades_csv_path = os.path.join(run_dir, trades_filename)
    orders_csv_path = os.path.join(run_dir, orders_filename)
    history_orders_csv_path = os.path.join(run_dir, history_filename)

    # Формируем словарь для передачи в Engine
    all_params = {
        'instruments_metainfo': config['instruments_metainfo'],
        'instruments': config['instruments'],
        'brokers': config['brokers'],
        'strategy': config['strategy'],
        'info': config['strategy_info'],
        'dir': run_dir
    }

    # Команда запуска
    command = [
        sys.executable,
        'core/engine.py',
        '--params', json.dumps(all_params),
        '--logs'
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    print("STDOUT:", result)

    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Ошибка парсинга JSON из stdout Engine: {e}")
        return

    print_output = output.copy()
    print_output.pop('logs',None)

    # Отладка
    print("=== DEBUG ===")
    print("Return code:", result.returncode)
    print("STDOUT:", print_output)
    print("STDERR:", repr(result.stderr))
    print("=== END DEBUG ===")

    if result.returncode != 0:
        print("Engine завершился с ошибкой. Выход.")
        return

    logs = output.get('logs', [])
    if not logs:
        print("Нет данных логов.")
        return

    trades = []
    open_trades = {}
    orders = []
    history_orders_seen = set()
    history_orders = []

    for entry in logs:
        dt = entry['datetime']
        current_positions = entry['positions']
        balance = entry['balance']

        for order in entry.get("pending_orders", []):
            orders.append({
                "open_time": order["created_at"],
                "symbol": order["symbol"],
                "side": order["side"],
                "volume": order["volume"],
                "order_type": order["order_type"],
                "limit_price": order["limit_price"],
                "trigger_price": order["trigger_price"],
                "linked_position_id": order["linked_position_id"],
                "take_profit": order["take_profit"],
                "stop_loss": order["stop_loss"],
            })

        for order in entry.get("history_orders", []):
            if order["id"] in history_orders_seen:
                continue
            history_orders_seen.add(order["id"])
            history_orders.append({
                "id": order["id"],
                "symbol": order["symbol"],
                "side": order["side"],
                "order_type": order["order_type"],
                "status": order["status"],
                "volume": order["volume"],
                "filled_price": order["filled_price"],
                "filled_volume": order["filled_volume"],
                "trigger_price": order["trigger_price"],
                "linked_position_id": order["linked_position_id"],
                "take_profit": order["take_profit"],
                "stop_loss": order["stop_loss"],
                "created_at": order["created_at"],
                "filled_at": order["filled_at"],
            })

        instruments_with_pos = set(current_positions.keys())

        # Открытие новых позиций
        for instr in instruments_with_pos:
            pos = current_positions[instr]
            if pos:  # есть позиция (непустой dict)
                if instr not in open_trades:
                    open_trades[instr] = {
                        'instrument': instr,
                        'open_time': dt,
                        'direction': pos['direction'],
                        'volume': pos['volume'],
                        'entry_price': pos['entry_price'],
                        'open_balance': balance
                    }
            else:
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
    plt.savefig(equity_plot_path, dpi=150)
    plt.show()

    # --- Сохранение сделок и ордеров в CSV ---
    with open(trades_csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['instrument', 'open_time', 'direction', 'volume', 'entry_price',
                      'take_profit', 'stop_loss', 'close_time', 'pnl', 'open_balance']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trades)

    with open(orders_csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["open_time","symbol","side","volume","order_type","limit_price","trigger_price","linked_position_id",
    "take_profit","stop_loss",]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(orders)
    with open(history_orders_csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["id", "symbol", "side", "order_type", "status", "volume",
                      "filled_price", "filled_volume", "trigger_price",
                      "linked_position_id", "take_profit", "stop_loss",
                      "created_at", "filled_at"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(history_orders)

    print(f"Записано {len(history_orders)} исполненных/отменённых ордеров в {history_orders_csv_path}")


    print(f"Записано {len(orders)} ордеров в {orders_csv_path}")
    print(f"Записано {len(trades)} сделок в {trades_csv_path}")

    print(f"График сохранён как {equity_plot_path}")

    # --- Сохранение сводки (summary) ---
    summary_path = os.path.join(run_dir, 'summary.txt')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("=== TRADING ENGINE SUMMARY ===\n")
        f.write(f"Run started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Информация о стратегии
        f.write(f"Strategy params: {config.get('strategy', 'N/A')}\n")
        f.write(f"Instruments: {config.get('instruments', [])}\n")
        f.write(f"Brokers: {config.get('brokers', [])}\n")
        if 'strategy_info' in config:
            f.write(f"Strategy info: {config['strategy_info']}\n")
        f.write("\n")

        # Данные из логов
        if logs:
            start_time = logs[0]['datetime']
            end_time = logs[-1]['datetime']
            start_balance = logs[0]['balance']
            end_balance = logs[-1]['balance']
            f.write(f"Start time: {start_time}\n")
            f.write(f"End time: {end_time}\n")
            f.write(f"Initial balance: {start_balance:.2f}\n")
            f.write(f"Final balance: {end_balance:.2f}\n")
            f.write(f"Total return: {(end_balance/start_balance - 1)*100:.2f}%\n")
        else:
            f.write("No log entries found.\n")

        # Статистика по закрытым сделкам
        closed_trades = [t for t in trades if t['close_time'] is not None]
        if closed_trades:
            pnls = [t['pnl'] for t in closed_trades if t['pnl'] is not None]
            if pnls:
                total_pnl = sum(pnls)
                avg_pnl = total_pnl / len(pnls)
                max_pnl = max(pnls)
                min_pnl = min(pnls)
                winning_trades = [p for p in pnls if p > 0]
                losing_trades = [p for p in pnls if p < 0]
                f.write(f"\n=== TRADES STATISTICS ===\n")
                f.write(f"Total closed trades: {len(closed_trades)}\n")
                f.write(f"Winning trades: {len(winning_trades)}\n")
                f.write(f"Losing trades: {len(losing_trades)}\n")
                f.write(f"Win rate: {len(winning_trades)/len(closed_trades)*100:.2f}%\n")
                f.write(f"Total PnL: {total_pnl:.2f}\n")
                f.write(f"Average PnL: {avg_pnl:.2f}\n")
                f.write(f"Max profit: {max_pnl:.2f}\n")
                f.write(f"Max loss: {min_pnl:.2f}\n")
            else:
                f.write("\nNo closed trades with valid PnL.\n")
        else:
            f.write("\nNo closed trades.\n")

        # Незакрытые позиции
        open_trades_count = len([t for t in trades if t['close_time'] is None])
        if open_trades_count:
            f.write(f"\nOpen positions remaining: {open_trades_count}\n")

    print(f"Сводка сохранена в {summary_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Single run of trading engine")
    parser.add_argument('--config', type=str, default=r'configs\single_run\portfolio_strategy.yaml',
                        help='Path to YAML configuration file')
    args = parser.parse_args()
 
    config = load_config(args.config)
    run_engine(config)