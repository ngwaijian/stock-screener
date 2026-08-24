import yfinance as yf
tickers = "AAPL MSFT TSLA"
df = yf.download(tickers, period="1mo", interval="1d")
print("Columns:", df.columns)
print("AAPL Close:", df['Close']['AAPL'].tail())
