import subprocess
import json

params = {
    "Market": "MOEX",          
    "Active": "adjusted_stock",          
    "Timeframe": "1d",            
    "Name": "GD_5min",         
    "Start": "2023-12-25",        
    "End": "2024-02-01",          
    "commissions": 0.0003,       
    "slippage": 0.00001,         
    "path": "Strategies/MA_cross.py", 
    "name": "MA_cross",           
    "short_period": 8,  
    "long_period": 198,
    "take_profit_percent":0.08073178111406797,    
    "stop_loss_percent": 0.27729899494779076      
}

command = ['python', 'Engine.py', '--params', json.dumps(params)]
result = subprocess.run(command, capture_output=True, text=True)

if result.returncode == 0:
    output = json.loads(result.stdout)
    print("Результаты тестирования:")
    print(f"  Total Return: {output['total_return']:.4f}")
    print(f"  Sharpe Ratio: {output['sharp_ratio']:.4f}")
    print(f"  Max Drawdown: {output['max_drawdown']:.2f}%")
    # print(output['positions_history'])
    if 'balances' in output:
        import matplotlib.pyplot as plt
        plt.plot(output['balances'])
        plt.title('Equity Curve')
        plt.xlabel('Time')
        plt.ylabel('Balance')
        plt.grid()
        plt.show()
else:
    print(f"Ошибка выполнения: {result.returncode}")
    print(result.stderr)
