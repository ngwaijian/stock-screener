import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import json
import os
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(page_title="Stock Screener (Jack & Turtle)", layout="wide")
st.title("📈 Stock Screener: Jack Investment & Turtle Trading")

with st.expander("📚 App Tutorials & Strategy Explanations (Click to expand)"):
    st.markdown("""
    ### 1. How to use this App
    - **Discovery Scanner:** Automatically scans top 30 liquid stocks in the US or Malaysia to find daily Buy/Watch signals.
    - **My Portfolio:** Track your existing stocks by appending `@price` to your ticker (e.g. `SUNCON@2.50`). The app will tell you when to Hold, Take Profit, or Cut Loss.

    ### 2. Status Legend
    - 🟢 **BUY SIGNAL**: All criteria met for a new entry (Trend is up, volume surge, breakout).
    - 🟡 **WATCH (Consolidating)**: Stock is pulling back to support, waiting for breakout.
    - 🟡 **HOLD**: For stocks you already own; trend is still intact.
    - 🔴 **SELL SIGNAL**: Trend is broken or the stock hit your Cut Loss (CL) level.
    - 🟢 **TAKE PROFIT**: Stock has reached your Take Profit (TP) target.
    - ⚪ **NO SIGNAL / IN TREND**: No actionable setup right now.

    ### 3. What is the 1:1.5 RR Target?
    **RR (Risk-Reward Ratio / 盈亏比)** is the core of Jack Investment's money management. 
    > *"每笔交易至少要具备 1.5 倍以上的盈亏比——如果亏的话会亏 100 块，那你就要确保赚的时候会赚到至少 150 块。"*
    - **Risk:** Entry Price - Cut Loss
    - **Reward:** Risk * 1.5
    - **TP Target:** Entry + Reward. When hit, sell 50-70% to lock in profit.

    ### 4. Strategy Logic & Formulas
    *   **EMA30 (30-Day EMA):** Used as the "Lifeline" for short-term trends.
    *   **High20 / Low20:** Defines the Breakout level and the Consolidation Box support.
    *   **Jack Investment Buy Criteria:** Uptrend (Close > EMA30) + Consolidation (Box size < 20%) + Breakout (Close > High20) + Volume Surge (Vol > 1.2x 20d Avg) + Strong Close (Close in upper half of candle).
    *   **Jack's Technical Score (/5):** +2 for Uptrend, +1 for Vol Surge, +1 for Consolidation, +1 for Breakout.
    *   **Turtle Trading Buy Criteria:** Breakout (Close > High20). Exit when Close < Low10.
    """)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_data(ticker):
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
    df = yf.download(ticker, period="1y", interval="1d", progress=False, session=session)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df

def calculate_indicators(df):
    if len(df) < 55:
        return df
    df['EMA30'] = df['Close'].ewm(span=30, adjust=False).mean()
    df['High20'] = df['High'].shift(1).rolling(window=20).max()
    df['Low20'] = df['Low'].shift(1).rolling(window=20).min()
    df['Low10'] = df['Low'].shift(1).rolling(window=10).min()
    df['Vol20'] = df['Volume'].shift(1).rolling(window=20).mean()
    df['PrevClose'] = df['Close'].shift(1)
    df['TR'] = df[['High', 'PrevClose']].max(axis=1) - df[['Low', 'PrevClose']].min(axis=1)
    df['ATR20'] = df['TR'].rolling(window=20).mean()
    return df

def analyze_jack_investment(df, latest, custom_entry=None):
    trend_up = latest['Close'] > latest['EMA30']
    box_size = (latest['High20'] - latest['Low20']) / latest['Low20']
    is_consolidating = box_size < 0.20
    is_breakout = latest['Close'] > latest['High20']
    vol_surge = latest['Volume'] > (1.2 * latest['Vol20'])
    upper_half = latest['Close'] > ((latest['High'] + latest['Low']) / 2)
    cl = latest['Low20'] * 0.98
    
    score = 0
    if trend_up: score += 2
    if vol_surge: score += 1
    if is_consolidating: score += 1
    if is_breakout: score += 1

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
        tp = entry + abs(entry - cl) * 1.5
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
        "Score": f"{score}/5",
        "Entry Price": entry,
        "Cut Loss (CL)": cl,
        "Take Profit (TP)": tp,
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
        "Score": "N/A",
        "Entry Price": entry,
        "Cut Loss (CL)": cl,
        "Take Profit (TP)": trailing_exit,
        "TA Summary": ", ".join(reasons) if reasons else ""
    }

@st.cache_data(ttl=86400, show_spinner=False)
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

def plot_interactive_chart(df, ticker_name, entry, tp, cl):
    df_plot = df.tail(90) # Last 90 days for better view
    fig = go.Figure(data=[go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name='Price')])
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA30'], mode='lines', name='EMA30', line=dict(color='orange', width=1.5)))
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['High20'], mode='lines', name='High20 (Resistance)', line=dict(color='blue', width=1, dash='dash')))
    fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Low20'], mode='lines', name='Low20 (Support)', line=dict(color='purple', width=1, dash='dash')))
    
    # Add Entry, TP, CL horizontal lines
    fig.add_hline(y=entry, line_dash="solid", line_color="blue", annotation_text=f"Entry: {entry:.2f}", annotation_position="top right")
    fig.add_hline(y=tp, line_dash="solid", line_color="green", annotation_text=f"TP: {tp:.2f}", annotation_position="top right")
    fig.add_hline(y=cl, line_dash="solid", line_color="red", annotation_text=f"CL: {cl:.2f}", annotation_position="bottom right")
    
    fig.update_layout(
        title=dict(text=f"Chart for {ticker_name}", font=dict(size=14)),
        xaxis_rangeslider_visible=False,
        template='plotly_white',
        margin=dict(t=60, b=10, l=10, r=50), # Tighter margins for mobile screens
        height=350, # Slightly shorter to fit on iPhone screen without hiding the app
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=10)), # Horizontal legend on top
        dragmode='pan' # Pan is much more mobile friendly than box select
    )
    return fig

def load_portfolio():
    if os.path.exists("portfolio.json"):
        try:
            with open("portfolio.json", "r") as f:
                return json.load(f)
        except:
            pass
    return {"US Stocks": "AAPL, TSLA@200, PLTR", "Malaysia Stocks": "SUNCON@3.00, MAYBANK, TENAGA"}

def save_portfolio(data):
    with open("portfolio.json", "w") as f:
        json.dump(data, f)

portfolio_data = load_portfolio()

def color_status(val):
    if val == 'BUY SIGNAL' or val == 'TAKE PROFIT': return 'color: green'
    elif val.startswith('WATCH') or val == 'IN TREND' or val == 'HOLD': return 'color: orange'
    elif val.startswith('SELL SIGNAL'): return 'color: red'
    return 'color: gray'

tab1, tab2 = st.tabs(["🎯 Discovery Scanner (Find New Buys)", "💼 My Portfolio (Check Holds/Sells)"])

with tab1:
    st.markdown("### Market Discovery Scanner")
    scan_market = st.selectbox("Select Market to Scan", ["Malaysia Top 30 (KLCI)", "US Tech Mega-Caps"])
    scan_strategy = st.selectbox("Strategy to Use", ["Jack Investment", "Turtle Trading (System 1)"], key="scan_strat")
    
    my_top_30 = ["MAYBANK.KL", "TENAGA.KL", "PBBANK.KL", "CIMB.KL", "PMETAL.KL", "YTL.KL", "YTLPOWR.KL", "DIALOG.KL", "IHH.KL", "CELCOMDIGI.KL", "TM.KL", "MRDIY.KL", "PETGAS.KL", "SIME.KL", "MISC.KL", "KLK.KL", "IOICORP.KL", "PPB.KL", "NESTLE.KL", "MAXIS.KL", "INARI.KL", "GENTING.KL", "GENM.KL", "AMBANK.KL", "RHBBANK.KL", "HLIB.KL", "CDB.KL", "SUNWAY.KL", "GAMUDA.KL"]
    us_top_30 = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "BRK-B", "TSM", "LLY", "V", "JPM", "UNH", "XOM", "MA", "JNJ", "PG", "HD", "COST", "ABBV", "MRK", "PEP", "CRM", "KO", "WMT", "NFLX", "BAC", "AMD", "PLTR"]
    
    if st.button("🚀 Run Full Market Scan"):
        scan_tickers = my_top_30 if "Malaysia" in scan_market else us_top_30
        results, charts_data = [], {}
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, ticker in enumerate(scan_tickers):
            status_text.text(f"Scanning {ticker}... ({i+1}/{len(scan_tickers)})")
            try:
                df = fetch_data(ticker)
                if len(df) < 55: 
                    st.warning(f"Not enough data for {ticker}. Yahoo Finance might be blocking the Cloud server.")
                    continue
                df = calculate_indicators(df)
                latest = df.iloc[-1]
                res = analyze_jack_investment(df, latest) if scan_strategy == "Jack Investment" else analyze_turtle_trading(df, latest)
                
                if res['Status'] in ["BUY SIGNAL", "WATCH (Consolidating)"]:
                    ticker_sym, shortname = resolve_ticker(ticker, "Malaysia Stocks" if "Malaysia" in scan_market else "US Stocks")
                    res['Stock'] = f"{shortname} ({ticker_sym})"
                    charts_data[res['Stock']] = (df, res['Entry Price'], res['Take Profit (TP)'], res['Cut Loss (CL)'])
                    
                    res['Entry Price'] = f"{res['Entry Price']:.2f}"
                    res['Cut Loss (CL)'] = f"{res['Cut Loss (CL)']:.2f}"
                    res['Take Profit (TP)'] = f"{res['Take Profit (TP)']:.2f}"
                    results.append(res)
            except Exception: pass
            progress_bar.progress((i + 1) / len(scan_tickers))
            
        status_text.text("Scan complete!")
        if results:
            results_df = pd.DataFrame(results)[['Stock', 'Score', 'Status', 'Entry Price', 'Cut Loss (CL)', 'Take Profit (TP)', 'TA Summary']]
            st.success(f"Found {len(results)} potential setups today!")
            
            # Export to CSV
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="📥 Download CSV", data=csv, file_name="screener_results.csv", mime="text/csv")
            
            st.dataframe(results_df.style.map(color_status, subset=['Status']))
            
            st.markdown("### 📊 Interactive Charts")
            for stock, (df, entry, tp, cl) in charts_data.items():
                with st.expander(f"View Chart: {stock}"):
                    st.plotly_chart(plot_interactive_chart(df, stock, entry, tp, cl), use_container_width=True, config={'displayModeBar': False, 'scrollZoom': True})
        else:
            st.info("No BUY or WATCH signals found today. The market might be weak or overextended.")

with tab2:
    st.markdown("### Manual / Portfolio Tracker")
    market = st.radio("Select Market", ["US Stocks", "Malaysia Stocks"], key="port_market")
    tickers_input = st.text_area("Your Saved Tickers (comma separated, use @price for entry)", portfolio_data[market])
    
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Save Portfolio"):
            portfolio_data[market] = tickers_input
            save_portfolio(portfolio_data)
            st.success("Saved!")
            
    strategy = st.selectbox("Select Strategy", ["Jack Investment", "Turtle Trading (System 1)"], key="port_strat")

    if st.button("🔍 Check Portfolio"):
        raw_inputs = [t.strip() for t in tickers_input.split(",") if t.strip()]
        parsed_items = []
        with st.spinner("Resolving stock names..."):
            for t in raw_inputs:
                if "@" in t:
                    parts = t.split("@")
                    try:
                        parsed_items.append((resolve_ticker(parts[0].strip(), market), float(parts[1].strip())))
                    except Exception as e: 
                        st.error(f"Error parsing price for {t}: {e}")
                else:
                    parsed_items.append((resolve_ticker(t, market), None))
                
        results, charts_data = [], {}
        progress_bar = st.progress(0)
        
        for i, ((ticker, shortname), custom_entry) in enumerate(parsed_items):
            try:
                df = fetch_data(ticker)
                if len(df) < 55: 
                    st.warning(f"Not enough data for {shortname} ({ticker}). Yahoo Finance might be blocking this Cloud server IP.")
                    continue
                df = calculate_indicators(df)
                latest = df.iloc[-1]
                
                res = analyze_jack_investment(df, latest, custom_entry) if strategy == "Jack Investment" else analyze_turtle_trading(df, latest, custom_entry)
                res['Stock'] = f"{shortname} ({ticker})"
                charts_data[res['Stock']] = (df, res['Entry Price'], res['Take Profit (TP)'], res['Cut Loss (CL)'])
                
                res['Entry Price'] = f"{res['Entry Price']:.2f}"
                res['Cut Loss (CL)'] = f"{res['Cut Loss (CL)']:.2f}"
                res['Take Profit (TP)'] = f"{res['Take Profit (TP)']:.2f}"
                results.append(res)
            except Exception as e:
                st.error(f"Error processing {shortname}: {e}")
            progress_bar.progress((i + 1) / len(parsed_items))
            
        if results:
            results_df = pd.DataFrame(results)[['Stock', 'Score', 'Status', 'Entry Price', 'Cut Loss (CL)', 'Take Profit (TP)', 'TA Summary']]
            st.dataframe(results_df.style.map(color_status, subset=['Status']))
            
            st.markdown("### 📊 Interactive Charts")
            for stock, (df, entry, tp, cl) in charts_data.items():
                with st.expander(f"View Chart: {stock}"):
                    st.plotly_chart(plot_interactive_chart(df, stock, entry, tp, cl), use_container_width=True, config={'displayModeBar': False, 'scrollZoom': True})
        else:
            st.info("No results found.")
