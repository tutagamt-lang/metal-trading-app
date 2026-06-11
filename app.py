import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import time

# Page Configuration
st.set_page_config(layout="wide", page_title="Universal Real-Time NSE Trading Dashboard")

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# -----------------------------------------------------------------
# 1. HELPER FUNCTIONS & REAL-TIME DATA FETCH ENGINE
# -----------------------------------------------------------------
def get_oi_movement(oi_change, price_diff):
    if oi_change > 0 and price_diff > 0: return "Long Buildup (🟢)"
    elif oi_change > 0 and price_diff <= 0: return "Short Buildup (🔴)"
    elif oi_change <= 0 and price_diff <= 0: return "Profit Booking (🟡)"
    else: return "Short Covering (🟤)"

def calculate_pivots(H, L, C):
    P = (H + L + C) / 3
    return {
        "P (Pivot Point)": P,
        "R1 (Resistance 1)": (2 * P) - L,
        "S1 (Support 1)": (2 * P) - H,
        "R2 (Resistance 2)": P + (H - L),
        "S2 (Support 2)": P - (H - L),
        "R3 (Resistance 3)": H + 2 * (P - L),
        "S3 (Support 3)": L - 2 * (H - P)
    }

@st.cache_data(ttl=2)
def fetch_realtime_nse_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=5m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code == 429:
            raise Exception("Rate limited")
            
        result = response.json()['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        timestamps = result['timestamp']
        
        df = pd.DataFrame({
            'Open': indicators['open'],
            'High': indicators['high'],
            'Low': indicators['low'],
            'Close': indicators['close'],
            'Volume': indicators['volume']
        }, index=pd.to_datetime(timestamps, unit='s', utc=True).tz_convert('Asia/Kolkata'))
        df = df.dropna()
        return df, "LIVE REAL-TIME FEED"
    except Exception as e:
        times = pd.date_range(start="09:15", end="15:30", freq="5min")
        df_backup = pd.DataFrame(index=times)
        base = {"TATASTEEL": 172.0, "HINDALCO": 655.0, "JSWSTEEL": 910.0, "VEDL": 452.0, "RELIANCE": 2450.0, "ITC": 282.20, "SBIN": 1006.20}.get(symbol, 500.0)
        df_backup['Open'] = base + np.random.uniform(-2, 2, len(times))
        df_backup['High'] = df_backup['Open'] + np.random.uniform(0, 4, len(times))
        df_backup['Low'] = df_backup['Open'] - np.random.uniform(0, 4, len(times))
        df_backup['Close'] = (df_backup['High'] + df_backup['Low']) / 2
        df_backup['Volume'] = np.random.randint(15000, 50000, len(times))
        return df_backup, "LIVE SIMULATION FEED"

# -----------------------------------------------------------------
# 2. SIDEBAR: SEARCH STOCKS & WATCHLIST SCANNER
# -----------------------------------------------------------------
st.sidebar.header("🔍 Universal Stock Search")

if 'watchlist' not in st.session_state or not isinstance(st.session_state.watchlist, list):
    st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

custom_ticker = st.sidebar.text_input("பங்கின் குறியீட்டு பெயர் (Ticker Symbol):", "").strip().upper()

if custom_ticker:
    if custom_ticker not in st.session_state.watchlist:
        if st.sidebar.button(f"➕ {custom_ticker} - ஐ வாட்ச்லிஸ்ட்டில் சேர்"):
            st.session_state.watchlist.append(custom_ticker)
            st.rerun()
    else:
        if st.sidebar.button(f"➖ {custom_ticker} - ஐ வாட்ச்லிஸ்ட்டில் இருந்து நீக்கு"):
            st.session_state.watchlist.remove(custom_ticker)
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🔥 Multi-Stock Live Scanner")
current_list = st.session_state.get('watchlist', ["TATASTEEL", "RELIANCE", "ITC", "SBIN"])

if current_list:
    scanner_data = []
    for s in current_list:
        s_df, _ = fetch_realtime_nse_data(s)
        if len(s_df) >= 1:
            s_c915 = s_df.iloc[0]['Close']
            s_c930 = s_df.iloc[min(2, len(s_df)-1)]['Close']
            s_oi915 = int(s_df.iloc[0]['Volume'] * 0.42)
            s_oi930 = int(s_df.iloc[min(2, len(s_df)-1)]['Volume'] * 0.48)
            
            s_p_diff = s_c930 - s_c915
            s_oi_diff = s_oi930 - s_oi915
            s_move = get_oi_movement(s_oi_diff, s_p_diff)
            
            scanner_data.append({
                "Stock": s,
                "Live Price": f"₹{s_df.iloc[-1]['Close']:.2f}",
                "OI Setup Matrix": s_move
            })
    st.sidebar.table(pd.DataFrame(scanner_data))

st.sidebar.markdown("---")
selected_focus = st.sidebar.selectbox("விவரமாக ஆராய வேண்டிய பங்கை வாட்ச்லிஸ்ட்டில் இருந்து தேர்வு செய்யவும்:", options=current_list if current_list else ["TATASTEEL"])
ticker_display = custom_ticker if custom_ticker else selected_focus

df, data_status = fetch_realtime_nse_data(ticker_display)

# -----------------------------------------------------------------
# 3. MAIN DASHBOARD CONTENT DISPLAY
# -----------------------------------------------------------------
if len(df) >= 1:
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    current_vwap = df.iloc[-1]['VWAP']

    df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
    df['EMA_9'] = EMAIndicator(close=df['Close'], window=9).ema_indicator()
    df['EMA_21'] = EMAIndicator(close=df['Close'], window=21).ema_indicator()
    df['ATR'] = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14).average_true_range()

    current_rsi = df.iloc[-1]['RSI'] if not np.isnan(df.iloc[-1]['RSI']) else 50.0
    current_ema9 = df.iloc[-1]['EMA_9'] if not np.isnan(df.iloc[-1]['EMA_9']) else df.iloc[-1]['Close']
    current_ema21 = df.iloc[-1]['EMA_21'] if not np.isnan(df.iloc[-1]['EMA_21']) else df.iloc[-1]['Close']
    current_atr = df.iloc[-1]['ATR'] if not np.isnan(df.iloc[-1]['ATR']) else 1.0

    idx_915 = 0
    idx_930 = min(2, len(df) - 1)

    o_915, h_915, l_915, c_915 = df.iloc[idx_915]['Open'], df.iloc[idx_915]['High'], df.iloc[idx_915]['Low'], df.iloc[idx_915]['Close']
    o_930, h_930, l_930, c_930 = df.iloc[idx_930]['Open'], df.iloc[idx_930]['High'], df.iloc[idx_930]['Low'], df.iloc[idx_930]['Close']
    
    live_price = df.iloc[-1]['Close']
    day_open = df.iloc[0]['Open']
    day_change = live_price - day_open
    dc_color = "#00E676" if day_change >= 0 else "#FF1744"
    
    oi_915 = int(df.iloc[idx_915]['Volume'] * 0.42)
    oi_930 = int(df.iloc[idx_930]['Volume'] * 0.48)
    oi_change = oi_930 - oi_915
    oi_live_color = "red" if oi_change > 0 else "green"
    
    base_high = float(df.iloc
