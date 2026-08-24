import json
import os
import pandas as pd

def load_portfolio():
    default = {
        "US Stocks": [{"Ticker": "AAPL", "Entry Price": 150.0, "Quantity": 10}, {"Ticker": "TSLA", "Entry Price": 200.0, "Quantity": 5}],
        "Malaysia Stocks": [{"Ticker": "MAYBANK", "Entry Price": 8.50, "Quantity": 1000}, {"Ticker": "SUNCON", "Entry Price": 3.00, "Quantity": 1000}]
    }
    if os.path.exists("portfolio.json"):
        try:
            with open("portfolio.json", "r") as f:
                data = json.load(f)
            # If it's the old string format, convert it
            if isinstance(data.get("US Stocks", ""), str):
                new_data = {"US Stocks": [], "Malaysia Stocks": []}
                for mkt in ["US Stocks", "Malaysia Stocks"]:
                    if mkt in data and isinstance(data[mkt], str):
                        for item in data[mkt].split(','):
                            item = item.strip()
                            if not item: continue
                            if "@" in item:
                                parts = item.split("@")
                                new_data[mkt].append({"Ticker": parts[0], "Entry Price": float(parts[1]), "Quantity": 100})
                            else:
                                new_data[mkt].append({"Ticker": item, "Entry Price": 0.0, "Quantity": 100})
                return new_data
            return data
        except Exception as e:
            print("Error loading", e)
            pass
    return default

print(load_portfolio())
