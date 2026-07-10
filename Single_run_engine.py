import subprocess
import json

params = {
    "Market": "MOEX",          
    "Active": "adjusted_stock",          
    "Timeframe": "1d",            
    "Name": "ABIO.MOEX",         
    "Start": "2023-08-18",        
    "End": "2026-07-08",          
    "commissions": 0.0003,       
    "slippage": 0.00001,         
    "path": "Strategies/MA_cross.py", 
    "name": "MA_cross",           
    "short_period": 10,  
    "long_period": 15,
    "take_profit_percent": 10.0,    
    "stop_loss_percent": 50.0      
}

command = ['python', 'Engine.py', '--params', json.dumps(params)]
result = subprocess.run(command, capture_output=True, text=True)

if result.returncode == 0:
    output = json.loads(result.stdout)
    print("Результаты тестирования:")
    print(f"  Total Return: {output['total_return']:.4f}")
    print(f"  Sharpe Ratio: {output['sharp_ratio']:.4f}")
    print(f"  Max Drawdown: {output['max_drawdown']:.2f}%")
    
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