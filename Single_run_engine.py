import subprocess
import json
import matplotlib.pyplot as plt
import pandas as pd
import csv
from datetime import datetime
import sys

data_params = [
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "ABIO.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "ABRD.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "AFKS.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "AFLT.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "AKRN.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "ALRS.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "AMEZ.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "APRI.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "APTK.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "AQUA.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "ARSA.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "ASSB.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "ASTR.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    },
    {
        'Market': "MOEX",
        'Active': "adjusted_stock",
        'Timeframe': "1d",
        'Name': "AVAN.MOEX",
        'Start': "2023-08-18",
        'End': "2026-07-08"
    }
]

brokers_params = {"commissions": 0.0001,       
                    "slippage": 0.0}

suggested = {"rebalance_period":50,    
            "max_lot": 0.01  }

strategy_info = {"path": r"Strategies\Portfolio_strategy.py", 
                "name": "Portfolio_strategy",  }

all_params = {
        'instruments': data_params,
        'brokers': brokers_params,
        'strategy': suggested,
        'info': strategy_info
    }

command = [sys.executable, 'core/Engine.py', '--params', json.dumps(all_params), '--logs']
result = subprocess.run(command, capture_output=True, text=True)
print("=== DEBUG ===")
print("Return code:", result.returncode)
print("STDOUT:", repr(result.stdout))   # покажет содержимое, даже если пусто
print("STDERR:", repr(result.stderr))
print("=== END DEBUG ===")
if result.returncode == 0:
    output = json.loads(result.stdout)
    logs = output.get('logs', [])
    if logs:
        # Определяем сделки по каждому инструменту (нужно ДО графика, чтобы отметить точки входа/выхода)
        trades = []
        open_trades = {}  # instrument -> open_trade_info

        for entry in logs:
            dt = entry['datetime']
            current_positions = entry['positions']  # словарь {instrument: [pos_dict, ...]}
            balance = entry['balance']

            # Проверяем, какие инструменты появились или исчезли
            instruments_with_pos = set(current_positions.keys())
            for instr in instruments_with_pos:
                pos_list = current_positions[instr]
                if pos_list:  # есть хотя бы одна позиция
                    if instr not in open_trades:
                        # Открываем сделку (берём первую позицию)
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
                    # Позиций нет – если была открыта, закрываем
                    if instr in open_trades:
                        trade = open_trades.pop(instr)
                        trade['close_time'] = dt
                        trade['pnl'] = balance - trade['open_balance']
                        trades.append(trade)

            # Также нужно обработать инструменты, которые были в open_trades, но отсутствуют в current_positions
            # (например, если все позиции закрыты)
            for instr in list(open_trades.keys()):
                if instr not in instruments_with_pos:
                    trade = open_trades.pop(instr)
                    trade['close_time'] = dt
                    trade['pnl'] = balance - trade['open_balance']
                    trades.append(trade)

        # Если остались незакрытые сделки в конце
        for instr, trade in open_trades.items():
            trade['close_time'] = None
            trade['pnl'] = None
            trades.append(trade)

        # График equity + просадка + отметки входа/выхода по сделкам
        dates = pd.to_datetime([entry['datetime'] for entry in logs])
        balances = pd.Series([entry['balance'] for entry in logs], index=dates)
        margins = pd.Series([entry['margin'] for entry in logs], index=dates)

        running_max = balances.cummax()
        drawdown = (balances - running_max) / running_max * 100

        fig, (ax_equity, ax_dd) = plt.subplots(
            2, 1, figsize=(12, 7), sharex=True,
            gridspec_kw={'height_ratios': [3, 1]}
        )

        ax_equity.plot(balances.index, balances.values, color='tab:blue', linewidth=1.2, label='Balance (equity)')
        ax_equity.plot(margins.index, margins.values, color='tab:orange', linewidth=1.2, linestyle='--', label='Margin (свободные деньги)')

        # маркеры входа (зелёный треугольник вверх) и выхода (красный треугольник вниз)
        open_times = pd.to_datetime([t['open_time'] for t in trades if t['open_time']])
        close_times = pd.to_datetime([t['close_time'] for t in trades if t.get('close_time')])
        if len(open_times):
            ax_equity.scatter(open_times, balances.reindex(open_times, method='nearest'),
                               marker='^', color='green', s=40, label='Открытие', zorder=3)
        if len(close_times):
            ax_equity.scatter(close_times, balances.reindex(close_times, method='nearest'),
                               marker='v', color='red', s=40, label='Закрытие', zorder=3)

        ax_equity.set_title('Balance & Margin')
        ax_equity.set_ylabel('Деньги')
        ax_equity.legend(loc='upper left')
        ax_equity.grid(alpha=0.3)



        fig.autofmt_xdate()
        fig.tight_layout()
        fig.savefig('equity.png', dpi=150)
        plt.show()

        # Сохраняем сделки в CSV
        with open('trades_log.csv', 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['instrument', 'open_time', 'direction', 'volume', 'entry_price',
                          'take_profit', 'stop_loss', 'close_time', 'pnl', 'open_balance']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(trades)

        print(f"Записано {len(trades)} сделок в trades_log.csv")