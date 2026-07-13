import subprocess
import json
import matplotlib.pyplot as plt
import csv
from datetime import datetime

params = {
    "Market": "MOEX",          
    "Active": "adjusted_stock",          
    "Timeframe": "1d",            
    "Name": "ABIO.MOEX",         
    "Start": "2024-08-01",        
    "End": "2026-12-16",          
    "commissions": 0.01,       
    "slippage": 0.0,         
    "path": "Strategies/MA_cross.py", 
    "name": "MA_cross",           
    "short_period": 8,  
    "long_period": 198,
    "take_profit_percent":0.001,    
    "stop_loss_percent": 0.001  
}

command = ['python', 'Engine.py', '--params', json.dumps(params), '--logs']
result = subprocess.run(command, capture_output=True, text=True)

if result.returncode == 0:
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print("Ошибка парсинга JSON. Содержимое stdout:")
        print(result.stdout)
        raise e

    if 'logs' in output and output['logs']:
        logs = output['logs']
        balances = [entry['balance'] for entry in logs]
        
        plt.figure(figsize=(12, 6))
        plt.plot(balances, label='Balance')
        plt.title('Equity Curve')
        plt.xlabel('Step')
        plt.ylabel('Balance')
        plt.grid(True)
        plt.legend()
        plt.savefig('equity.png')
        plt.show()

        trades = []
        prev_positions = []   
        open_trade = None     

        for i, entry in enumerate(logs):
            current_positions = entry['positions']  
            dt = entry['datetime'] 
            if not prev_positions and current_positions:
                pos = current_positions[0]  
                open_trade = {
                    'open_time': dt,
                    'direction': pos['direction'],
                    'volume': pos['volume'],
                    'entry_price': pos['entry_price'],
                    'take_profit': pos['take_profit'],
                    'stop_loss': pos['stop_loss'],
                    'open_balance': entry['balance']  
                }
            elif prev_positions and not current_positions:
                if open_trade is not None:
                    close_balance = entry['balance']
                    pnl = close_balance - open_trade['open_balance']  
                    open_trade['close_time'] = dt
                    open_trade['pnl'] = pnl
                    trades.append(open_trade)
                    open_trade = None

            prev_positions = current_positions

        if open_trade is not None:
            open_trade['close_time'] = None
            open_trade['pnl'] = None
            trades.append(open_trade)

        with open('trades_log.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['open_time', 'direction', 'volume', 'entry_price',
                                                'take_profit', 'stop_loss', 'close_time', 'pnl', 'open_balance'])
            writer.writeheader()
            writer.writerows(trades)

        print(f"Записано {len(trades)} сделок в trades_log.csv")

    print("Результаты тестирования:")
    print(f"  Total Return: {output['total_return']:.4f}")
    print(f"  Sharpe Ratio: {output['sharp_ratio']:.4f}")
    print(f"  Max Drawdown: {output['max_drawdown']:.2f}%")

else:
    print(f"Ошибка выполнения: {result.returncode}")
    print(result.stderr)