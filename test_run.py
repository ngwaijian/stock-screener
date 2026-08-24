import yfinance as yf
from stock_screener import fetch_data, calculate_indicators, analyze_turtle_trading

df = fetch_data('TSLA')
df = calculate_indicators(df)
latest = df.iloc[-1]
res = analyze_turtle_trading(df, latest, 340.0)
res['Entry Price'] = f"{res['Entry Price']:.2f}"
print(res)
