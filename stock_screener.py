import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

def calculate_indicators(df):
    if len(df) < 55:
        return df

    # Moving Averages
    df['EMA30'] = df['Close'].ewm(span=30, adjust=False).mean()
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    df['SMA200'] = df['Close'].rolling(window=200).mean()

    # Donchian Channels (20 and 10 days)
    df['High20'] = df['High'].shift(1).rolling(window=20).max()
    df['Low20'] = df['Low'].shift(1).rolling(window=20).min()
    df['Low10'] = df['Low'].shift(1).rolling(window=10).min()

    # Volume Average
    df['Vol20'] = df['Volume'].shift(1).rolling(window=20).mean()

    # Average True Range (ATR)
    df['PrevClose'] = df['Close'].shift(1)
    df['TR'] = df[['High', 'PrevClose']].max(axis=1) - df[['Low', 'PrevClose']].min(axis=1)
    df['ATR20'] = df['TR'].rolling(window=20).mean()

    return df

def analyze_jack_investment(df, latest, custom_entry=None):
    trend_up = latest['Close'] > latest['EMA30']
    
    # Box structure check
    box_size = (latest['High20'] - latest['Low20']) / latest['Low20']
    is_consolidating = box_size < 0.20 # 20% box tolerance
    
    # Breakout: Close > High20
    is_breakout = latest['Close'] > latest['High20']
    
    # Volume Surge: Volume > 1.2 * Vol20
    vol_surge = latest['Volume'] > (1.2 * latest['Vol20'])
    
    # Candle upper half
    upper_half = latest['Close'] > ((latest['High'] + latest['Low']) / 2)
    
    cl = latest['Low20'] * 0.98 # Support minus 2% buffer
    
    if custom_entry is not None:
        entry = custom_entry
        tp = entry + abs(entry - cl) * 1.5
        
        reasons = [f"Bought at {entry:.2f}"]
        if latest['Close'] < cl:
            status = "SELL SIGNAL"
            reasons.append("Hit Cut Loss (Support broken)")
        elif not trend_up:
            status = "SELL SIGNAL"
            reasons.append("Trend broken (Below EMA30)")
        elif latest['Close'] >= tp:
            status = "TAKE PROFIT"
            reasons.append("Reached 1:1.5 RR Target")
        else:
            status = "HOLD"
            reasons.append("Trend intact")
    else:
        entry = latest['Close']
        tp = entry + abs(entry - cl) * 1.5 # 1:1.5 Risk-Reward
        
        signal = trend_up and is_consolidating and is_breakout and vol_surge and upper_half
        
        reasons = []
        if trend_up: reasons.append("Uptrend")
        if is_consolidating: reasons.append("Consolidating")
        if is_breakout: reasons.append("Breakout")
        if vol_surge: reasons.append("Vol Surge")
        
        if signal:
            status = "BUY SIGNAL"
        elif is_consolidating and trend_up:
            status = "WATCH (Consolidating)"
        else:
            status = "NO SIGNAL"
        
    return {
        "Status": status,
        "Entry Price": f"{entry:.2f}",
        "Cut Loss (CL)": f"{cl:.2f}",
        "Take Profit (TP)": f"{tp:.2f} (1:1.5 RR)",
        "TA Summary": ", ".join(reasons) if reasons else "No clear pattern"
    }

def analyze_turtle_trading(df, latest, custom_entry=None):
    is_breakout = latest['Close'] > latest['High20']
    atr = latest['ATR20']
    trailing_exit = latest['Low10']
    
    if custom_entry is not None:
        entry = custom_entry
        cl = entry - (2 * atr)
        
        reasons = [f"Bought at {entry:.2f}"]
        if latest['Close'] < trailing_exit:
            status = "SELL SIGNAL"
            reasons.append("Dropped below 10-day low (Trailing)")
        elif latest['Close'] < cl:
            status = "SELL SIGNAL"
            reasons.append("Hit 2 ATR Cut Loss")
        else:
            status = "HOLD"
            reasons.append("Trend intact")
    else:
        entry = latest['Close']
        cl = entry - (2 * atr)
        
        if is_breakout:
            status = "BUY SIGNAL"
        elif latest['Close'] > latest['Low10']:
            status = "IN TREND"
        else:
            status = "NO SIGNAL"
            
        reasons = [f"Current ATR: {atr:.2f}"]
        if is_breakout: reasons.append("20-Day Breakout!")
        
    return {
        "Status": status,
        "Entry Price": f"{entry:.2f}",
        "Cut Loss (CL)": f"{cl:.2f} (2 ATR)",
        "Take Profit (TP)": f"Trailing Exit < {trailing_exit:.2f}",
        "TA Summary": ", ".join(reasons) if reasons else ""
    }

st.set_page_config(page_title="Stock Screener (Jack & Turtle)", layout="wide")
st.title("📈 Stock Screener: Jack Investment & Turtle Trading")

with st.expander("ℹ️ Status Legend (Click to expand)"):
    st.markdown("""
    - 🟢 **BUY SIGNAL**: All criteria met for a new entry (Trend is up, volume surge, breakout).
    - 🟡 **WATCH (Consolidating)**: Stock is pulling back to support, waiting for breakout.
    - 🟡 **HOLD**: For stocks you already own; trend is still intact.
    - 🔴 **SELL SIGNAL**: Trend is broken or the stock hit your Cut Loss (CL) level.
    - 🟢 **TAKE PROFIT**: Stock has reached your Take Profit (TP) target.
    - ⚪ **NO SIGNAL / IN TREND**: No actionable setup right now.
    """)

with st.expander("📖 什么是 1:1.5 RR Target？ (What does RR Target mean?)"):
    st.markdown("""
    **RR (Risk-Reward Ratio / 盈亏比)** 是交易中最核心的资金管理概念之一。当你在状态栏看到 **"Reached 1:1.5 RR Target"** 时，代表这支股票的当前价格，已经达到了预设的 1.5 倍获利目标，系统提示你应该 **TAKE PROFIT (主动止盈)**。

    ### 📘 摘自《Jack Investment》第17章（资金与仓位管理）：
    > *"我个人通常建议，每笔交易至少要具备 1.5 倍以上的盈亏比——如果亏的话会亏 100 块，那你就要确保赚的时候会赚到至少 150 块。在这样的盈亏结构下，一笔 1.5 : 1 的交易，你只需要约 40% 的胜率，就能达到长期不亏不赚的损益平衡点。"*

    **App 是如何计算的？**
    1. **Risk (风险/潜在亏损)** = `Entry Price (你的买入价)` - `Cut Loss (止损支撑位)`
    2. **Reward (回报/盈利目标)** = `Risk × 1.5`
    3. **TP Target (止盈目标价)** = `Entry Price` + `Reward`

    一旦股价达到这个 **TP Target**，就意味着你已经赚取了冒着风险换来的 1.5 倍回报。根据 Jack 的策略，此时你应该选择卖出 50%-70% 的持股来锁定利润 (Lock in profit)，剩余的持股则可以继续放着，通过移动止盈 (Trailing Stop) 去捕捉更大的涨幅！
    """)

with st.expander("🧠 Strategy Logic & Formulas (How the App Works)"):
    st.markdown("""
    To give you full transparency and confidence, here are the exact formulas and rules the app uses under the hood:

    ### 1. Common Technical Indicators
    *   **EMA30 (30-Day Exponential Moving Average):** Used as the "Lifeline" (生命线) for short-term trends.
    *   **High20 / Low20:** The highest High and lowest Low of the previous 20 trading days. Used for Breakouts and defining the Consolidation Box (箱体).
    *   **Vol20 (20-Day Average Volume):** The average trading volume over the last 20 days.
    *   **ATR20 (20-Day Average True Range):** Measures market volatility.

    ---
    ### 2. Jack Investment Strategy
    Based on the "Trend + Consolidation + Breakout" philosophy.

    **Buy Signal Criteria (All must be TRUE):**
    1.  **Uptrend:** Current Close > EMA30.
    2.  **Consolidation (箱体整理):** The 20-day box size `(High20 - Low20) / Low20` must be less than 20% (indicating tight consolidation).
    3.  **Breakout:** Current Close > High20 (Price breaks the top of the box).
    4.  **Volume Surge:** Current Volume > 1.2 × Vol20 (Volume is 20% higher than the 20-day average).
    5.  **Strong Close:** Current Close is in the upper half of today's candle: `Close > (High + Low) / 2`.

    **Risk Management:**
    *   **Cut Loss (CL):** `Low20 × 0.98` (The bottom of the 20-day consolidation box, minus a 2% safety buffer to avoid false breakdowns).
    *   **Take Profit (TP):** `Entry Price + (Entry Price - CL) × 1.5` (Strict 1:1.5 Risk-Reward ratio).

    ---
    ### 3. Turtle Trading Strategy (System 1)
    Based on the classic Turtle trend-following rules.

    **Buy Signal Criteria:**
    1.  **Breakout:** Current Close > High20.

    **Risk Management:**
    *   **Cut Loss (CL):** `Entry Price - (2 × ATR20)` (Stop loss based on market volatility, not fixed percentages).
    *   **Take Profit (TP):** Exit when `Current Close < Low10` (A 10-day trailing stop to ride the trend as long as possible).
    """)

def resolve_ticker(query, market):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=3&newsCount=0"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        if 'quotes' in data and len(data['quotes']) > 0:
            if market == "Malaysia Stocks":
                for q in data['quotes']:
                    if q.get('exchange') == 'KLS' or q.get('symbol', '').endswith('.KL'):
                        return q['symbol'], q.get('shortname', q['symbol'])
            else:
                for q in data['quotes']:
                    if q.get('exchange') in ['NMS', 'NYQ', 'NCM', 'NGM']:
                        return q['symbol'], q.get('shortname', q['symbol'])
            return data['quotes'][0]['symbol'], data['quotes'][0].get('shortname', data['quotes'][0]['symbol'])
    except Exception:
        pass
    return query, query

def color_status(val):
    if val == 'BUY SIGNAL' or val == 'TAKE PROFIT':
        color = 'green'
    elif val.startswith('WATCH') or val == 'IN TREND' or val == 'HOLD':
        color = 'orange'
    elif val.startswith('SELL SIGNAL'):
        color = 'red'
    else:
        color = 'gray'
    return f'color: {color}'

# Tabs for different modes
tab1, tab2 = st.tabs(["🎯 Discovery Scanner (Find New Buys)", "💼 My Portfolio (Check Holds/Sells)"])

with tab1:
    st.markdown("### Market Discovery Scanner")
    st.markdown("Scan top blue-chip and high-volume stocks automatically to find fresh **BUY** setups for today.")
    
    scan_market = st.selectbox("Select Market to Scan", ["Malaysia Top 30 (KLCI)", "US Tech Mega-Caps"])
    scan_strategy = st.selectbox("Strategy to Use", ["Jack Investment", "Turtle Trading (System 1)"], key="scan_strat")
    
    my_top_30 = ["MAYBANK.KL", "TENAGA.KL", "PBBANK.KL", "CIMB.KL", "PMETAL.KL", "YTL.KL", "YTLPOWR.KL", "DIALOG.KL", "IHH.KL", "CELCOMDIGI.KL", "TM.KL", "MRDIY.KL", "PETGAS.KL", "SIME.KL", "MISC.KL", "KLK.KL", "IOICORP.KL", "PPB.KL", "NESTLE.KL", "MAXIS.KL", "INARI.KL", "GENTING.KL", "GENM.KL", "AMBANK.KL", "RHBBANK.KL", "HLIB.KL", "CDB.KL", "SUNWAY.KL", "GAMUDA.KL"]
    us_top_30 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "BRK-B", "TSM", "LLY", "V", "JPM", "UNH", "XOM", "MA", "JNJ", "PG", "HD", "COST", "ABBV", "MRK", "PEP", "CRM", "KO", "WMT", "NFLX", "BAC", "AMD", "PLTR"]
    
    if st.button("🚀 Run Full Market Scan"):
        scan_tickers = my_top_30 if "Malaysia" in scan_market else us_top_30
        
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, ticker in enumerate(scan_tickers):
            status_text.text(f"Scanning {ticker}... ({i+1}/{len(scan_tickers)})")
            try:
                df = yf.download(ticker, period="1y", interval="1d", progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                if len(df) < 55:
                    continue
                    
                df = calculate_indicators(df)
                latest = df.iloc[-1]
                
                if scan_strategy == "Jack Investment":
                    res = analyze_jack_investment(df, latest, None)
                else:
                    res = analyze_turtle_trading(df, latest, None)
                
                # ONLY keep actionable ideas
                if res['Status'] in ["BUY SIGNAL", "WATCH (Consolidating)"]:
                    # Fetch shortname
                    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={ticker}&quotesCount=1&newsCount=0"
                    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
                    shortname = r.json()['quotes'][0].get('shortname', ticker) if r.json().get('quotes') else ticker
                    
                    res['Stock'] = f"{shortname} ({ticker})"
                    results.append(res)
                    
            except Exception:
                pass
                
            progress_bar.progress((i + 1) / len(scan_tickers))
            
        status_text.text("Scan complete!")
        if results:
            results_df = pd.DataFrame(results)
            cols = ['Stock', 'Status', 'Entry Price', 'Cut Loss (CL)', 'Take Profit (TP)', 'TA Summary']
            results_df = results_df[cols]
            st.success(f"Found {len(results)} potential setups today!")
            st.dataframe(results_df.style.map(color_status, subset=['Status']))
        else:
            st.info("No BUY or WATCH signals found in the top 30 stocks today. The market might be weak or overextended.")

with tab2:
    st.markdown("### Manual / Portfolio Tracker")
    st.markdown("Manually check specific stocks. **Tip:** Append `@price` to track stocks you already own (e.g. `SUNCON@2.50`)")
    
    market = st.radio("Select Market", ["US Stocks", "Malaysia Stocks"], key="port_market")
    default_my = "SUNCON@3.00, MAYBANK, TENAGA"
    default_us = "AAPL, TSLA@200, PLTR"
    tickers_input = st.text_area("Enter Tickers (comma separated)", default_us if "US" in market else default_my)
    strategy = st.selectbox("Select Strategy", ["Jack Investment", "Turtle Trading (System 1)"], key="port_strat")

    if st.button("🔍 Check Portfolio / Tickers"):
        raw_inputs = [t.strip() for t in tickers_input.split(",") if t.strip()]
        parsed_items = []
        
        with st.spinner("Resolving stock names..."):
            for t in raw_inputs:
                if "@" in t:
                    parts = t.split("@")
                    name_query = parts[0].strip()
                    try:
                        price = float(parts[1].strip())
                    except:
                        price = None
                    ticker, shortname = resolve_ticker(name_query, market)
                    parsed_items.append((ticker, shortname, price))
                else:
                    ticker, shortname = resolve_ticker(t, market)
                    parsed_items.append((ticker, shortname, None))
                
        results = []
        progress_bar = st.progress(0)
        
        for i, item in enumerate(parsed_items):
            ticker, shortname, custom_entry = item
            try:
                df = yf.download(ticker, period="1y", interval="1d", progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)
                if len(df) < 55:
                    st.warning(f"Not enough data for {shortname} ({ticker})")
                    continue
                    
                df = calculate_indicators(df)
                latest = df.iloc[-1]
                
                if strategy == "Jack Investment":
                    res = analyze_jack_investment(df, latest, custom_entry)
                else:
                    res = analyze_turtle_trading(df, latest, custom_entry)
                    
                res['Stock'] = f"{shortname} ({ticker})"
                results.append(res)
                
            except Exception as e:
                st.error(f"Error processing {shortname} ({ticker}): {e}")
                
            progress_bar.progress((i + 1) / len(parsed_items))
            
        if results:
            results_df = pd.DataFrame(results)
            cols = ['Stock', 'Status', 'Entry Price', 'Cut Loss (CL)', 'Take Profit (TP)', 'TA Summary']
            results_df = results_df[cols]
            st.dataframe(results_df.style.map(color_status, subset=['Status']))
        else:
            st.info("No results found.")
