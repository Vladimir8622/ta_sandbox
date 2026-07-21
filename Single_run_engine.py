import subprocess
import json
import matplotlib.pyplot as plt
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

command = [sys.executable, 'Engine.py', '--params', json.dumps(all_params), '--logs']
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
        # График баланса
        balances = [entry['balance'] for entry in logs]
        plt.figure(figsize=(12,6))
        plt.plot(balances)
        plt.title('Equity Curve')
        plt.savefig('equity.png')
        plt.show()

        # Определяем сделки по каждому инструменту
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

        # Сохраняем сделки в CSV
        with open('trades_log.csv', 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['instrument', 'open_time', 'direction', 'volume', 'entry_price',
                          'take_profit', 'stop_loss', 'close_time', 'pnl', 'open_balance']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(trades)

        print(f"Записано {len(trades)} сделок в trades_log.csv")