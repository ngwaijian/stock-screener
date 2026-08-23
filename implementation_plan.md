# Stock Screener App Implementation Plan

## Goal
Build a real-time stock screener web application using Python and Streamlit. The app will analyze Malaysian and US stocks and generate Technical Analysis (TA), Entry Prices, Take Profit (TP), and Cut Loss (CL) levels based on the trading philosophies of two books:
1. **海龟交易法则 (Way of the Turtle)**
2. **Jack Investment (10_JACK INVESTMENT.pdf)**

## User Review Required
> [!IMPORTANT]
> Please review the chosen trading logic below. Since trading strategies require precise mathematical parameters, I have extracted the core rules from both books. Let me know if you want to tweak any of these parameters (e.g., Risk-Reward ratio, specific Moving Averages).

## Open Questions
- Do you have a specific list of stock tickers you want to monitor by default, or should the app allow you to input any ticker manually?
- `yfinance` provides data for US and Malaysian stocks (e.g., `MAYBANK.KL`), but real-time data might have a slight 15-minute delay depending on the exchange. Is this acceptable for your daily screening?

## Proposed Changes

### [NEW] `stock_screener.py`
We will create a standalone Python application using `streamlit` for the UI, `yfinance` for market data, and `pandas`/`pandas_ta` for technical indicators.

#### Core Strategy Logic

**1. Jack Investment Strategy (Trend Following & Box Breakout)**
Based on the PDF, Jack favors mid-to-short-term trend following (Swing Trading).
*   **Trend Filter:** Price must be in a general uptrend.
*   **Entry Signal:** Price pulls back to the EMA 30 (the "Life Line"), forms a consolidation box, and breaks out above the recent 20-day high with a volume surge (Volume > 1.2x of the 20-day average volume). The daily closing price must be in the upper half of the candle.
*   **Cut Loss (CL):** Set at the recent swing low (bottom of the box) minus a 1-2% buffer to avoid false breakdowns.
*   **Take Profit (TP):** Target a Risk:Reward ratio of at least 1:1.5. If the trade risks $100, the target is $150 profit.

**2. Turtle Trading Strategy (Donchian Channel Breakout)**
Based on the classic Turtle rules (System 1).
*   **Entry Signal:** Price breaks above the 20-day high.
*   **Cut Loss (CL):** Entry price minus 2 * ATR (Average True Range).
*   **Take Profit (TP):** Trailing stop - exit when the price drops below the 10-day low.

#### Application Features
*   **Sidebar:** Input for stock tickers (US and MY markets) and strategy selection.
*   **Data Fetching:** Downloads recent daily data to calculate moving averages (EMA 30, SMA 50, SMA 200), ATR, and Donchian Channels.
*   **Results Dashboard:** Displays a table with "Signal", "Entry Price", "TP", "CL", and a "TA Summary" explaining the rationale.

## Verification Plan
1.  Run the application locally using Streamlit.
2.  Input popular US stocks (e.g., AAPL, TSLA) and MY stocks (e.g., MAYBANK.KL, TENAGA.KL).
3.  Verify that the technical indicators and TP/CL levels are calculated correctly according to the defined formulas.
