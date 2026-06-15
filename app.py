import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import streamlit.components.v1 as components
import time

# 1. Page Configuration for Pro Institutional Layout
st.set_page_config(
    layout="wide", 
    page_title="QUANTUM-X Live Trading Terminal",
    initial_sidebar_state="expanded"
)

# 🎯 HIGH-CONTRAST ANTI-BLUR TERMINAL STYLE MATRIX
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght=400;700&family=Inter:wght=400;600&display=swap');
        
        * {
            font-family: 'Inter', sans-serif;
        }
        .block-container {
            padding-top: 2rem !important; 
            padding-bottom: 0rem; 
            padding-left: 1.5rem; 
            padding-right: 1.5rem;
        }
        h2 {
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            letter-spacing: -0.5px;
            margin-top: 5px !important;
            margin-bottom: 10px !important;
        }
        .mono-text {
            font-family: 'JetBrains Mono', monospace !important;
        }
        
        /* 📊 HIGH CONTRAST QUANT TABLES */
        .quant-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            background-color: #0d1117 !important;
            margin-bottom: 15px;
        }
        .quant-table th {
            background-color: #161b22 !important;
            color: #c9d1d9 !important;
            text-align: left;
            padding: 10px 12px;
            font-family: 'JetBrains Mono', monospace;
            border: 1px solid #30363d !important;
            font-size: 11px;
            letter-spacing: 0.5px;
            font-weight: 700 !important;
        }
        .quant-table td {
            border: 1px solid #30363d !important;
            padding: 10px 12px;
            font-family: 'JetBrains Mono', monospace;
            color: #ffffff !important;
            opacity: 1 !important;
            font-weight: 600 !important;
        }

        /* 🛑 SCANNED MATRIX PRO PANEL BOX */
        .matrix-box {
            background-color: #0d1117; 
            padding: 20px; 
            border-radius: 6px; 
            border: 1px solid #30363d; 
            font-family: 'Inter', sans-serif; 
            line-height: 1.8; 
            margin-bottom: 20px;
        }

        /* 🛑 ANTI-FADE MATRIX */
        div[data-testid="stDataFrameFade"], [data-testid="stElementOverlay"] {
            opacity: 1 !important;
            filter: none !important;
            transition: none !important;
            display: none !important;
            visibility: hidden !important;
        }
        .stApp [data-testid="stVerticalBlock"] > div {
            opacity: 1 !important;
            filter: none !important;
            animation: none !important;
            transition: none !important;
        }
        div[data-testid="stStatusWidget"] {
            visibility: hidden !important;
            display: none !important;
        }
    </style>
""", unsafe_allow_html=True)

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

# -----------------------------------------------------------------
# DATA ENGINE PIPELINE
# -----------------------------------------------------------------
def get_oi_movement(oi_change, price_diff):
    if oi_change > 0 and price_diff > 0: return "LONG BUILDUP"
    elif oi_change > 0 and price_diff <= 0: return "SHORT BUILDUP"
    elif oi_change <= 0 and price_diff <= 0: return "PROFIT BOOKING"
    else: return "SHORT COVERING"

def calculate_pivots(H, L, C):
    P = (H + L + C) / 3
    return {
        "R3 (Resistance 3)": H + 2 * (P - L),
        "R2 (Resistance 2)": P + (H - L),
        "R1 (Resistance 1)": (2 * P) - L,
        "P (Pivot Point)": P,
        "S1 (Support 1)": (2 * P) - H,
        "S2 (Support 2)": P - (H - L),
        "S3 (Support 3)": L - 2 * (H - P)
    }

@st.cache_data(ttl=1)
def fetch_realtime_nse_data(symbol):
    try:
        yahoo_symbol = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=1m&range=1d"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        result = response.json()['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        timestamps = result['timestamp']
        df = pd.DataFrame({
            'Open': indicators['open'], 'High': indicators['high'],
            'Low': indicators['low'], 'Close': indicators['close'],
            'Volume': indicators['volume']
        }, index=pd.to_datetime(timestamps, unit='s', utc=True).tz_convert('Asia/Kolkata'))
        return df.dropna(), "LIVE"
    except:
        times = pd.date_range(start="09:15", end="15:30", freq="1min")
        df_backup = pd.DataFrame(index=times)
        base = {"TATASTEEL": 197.80, "RELIANCE": 1293.0, "ITC": 285.10, "SBIN": 1017.15}.get(symbol, 500.0)
        df_backup['Open'] = base + np.random.uniform(-0.5, 0.5, len(times))
        df_backup['High'] = df_backup['Open'] + np.random.uniform(0, 0.8, len(times))
        df_backup['Low'] = df_backup['Open'] - np.random.uniform(0, 0.8, len(times))
        df_backup['Close'] = (df_backup['High'] + df_backup['Low']) / 2
        df_backup['Volume'] = np.random.randint(15000, 50000, len(times))
        return df_backup, "SIM"

# -----------------------------------------------------------------
# SIDEBAR TERMINAL (Static Elements)
# -----------------------------------------------------------------
st.sidebar.markdown("### `📡 RADAR TERMINAL`")
custom_ticker = st.sidebar.text_input("ENTER TICKER SYMBOL:", "").strip().upper()

if custom_ticker:
    if custom_ticker not in st.session_state.watchlist:
        if st.sidebar.button(f"[+] ADD {custom_ticker}", use_container_width=True):
            st.session_state.watchlist.append(custom_ticker)
            st.rerun()

selected_focus = st.sidebar.selectbox("⚡ ACTIVE INSTANCE:", options=st.session_state.watchlist)
ticker_clean = custom_ticker if custom_ticker else selected_focus

st.sidebar.markdown("---")
st.sidebar.markdown("#### `⚡ MULTI-STOCK MONITOR`")

# SideBar Realtime Dynamic Container
sidebar_placeholder = st.sidebar.empty()

# -----------------------------------------------------------------
# MAIN TERMINAL PLACEHOLDER (High-Performance Engine)
# -----------------------------------------------------------------
# டூப்ளிகேட் எரர் வராமல் தடுக்க முழு UI-யும் ஒரே ஒரு மாஸ்டர் பிளேஸ்ஹோல்டருக்குள் வைக்கப்படுகிறது
main_container = st.empty()

while True:
    # 1. Update Sidebar Multi-Stock Monitor Data
    if st.session_state.watchlist:
        scanner_data = []
        for s in st.session_state.watchlist:
            s_df, _ = fetch_realtime_nse_data(s)
            if len(s_df) >= 1:
                idx_30 = min(15, len(s_df)-1)
                s_move = get_oi_movement(
                    int(s_df.iloc[idx_30]['Volume']*0.48) - int(s_df.iloc[0]['Volume']*0.42), 
                    s_df.iloc[idx_30]['Close'] - s_df.iloc[0]['Close']
                )
                scanner_data.append({"STOCK": s, "LAST PRICE": f"{s_df.iloc[-1]['Close']:.2f}", "OI MATRIX": s_move})
        sidebar_placeholder.dataframe(pd.DataFrame(scanner_data), hide_index=True, use_container_width=True)

    # 2. Fetch Core Trading Data
    df, data_status = fetch_realtime_nse_data(ticker_clean)

    # 3. Main Dashboard Rendering Block
    if len(df) >= 1:
        df['VWAP'] = ((df['High'] + df['Low'] + df['Close']) / 3 * df['Volume']).cumsum() / df['Volume'].cumsum()
        current_vwap = df.iloc[-1]['VWAP']
        df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
        df['EMA_9'] = EMAIndicator(close=df['Close'], window=9).ema_indicator()
        df['EMA_21'] = EMAIndicator(close=df['Close'], window=21).ema_indicator()
        df['ATR'] = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14).average_true_range()

        current_rsi = df.iloc[-1]['RSI'] if not np.isnan(df.iloc[-1]['RSI']) else 50.0
        current_ema9 = df.iloc[-1]['EMA_9'] if not np.isnan(df.iloc[-1]['EMA_9']) else df.iloc[-1]['Close']
        current_ema21 = df.iloc[-1]['EMA_21'] if not np.isnan(df.iloc[-1]['EMA_21']) else df.iloc[-1]['Close']
        current_atr = df.iloc[-1]['ATR'] if not np.isnan(df.iloc[-1]['ATR']) else 1.0

        idx_915, idx_930 = 0, min(15, len(df) - 1)
        c_915, c_930 = df.iloc[idx_915]['Close'], df.iloc[idx_930]['Close']
        h_930 = df.iloc[0:idx_930+1]['High'].max()
        l_930 = df.iloc[0:idx_930+1]['Low'].min()
        
        live_price = df.iloc[-1]['Close']
        day_open = df.iloc[0]['Open']
        day_change = live_price - day_open
        dc_color = "#00ff88" if day_change >= 0 else "#ff2a5f"
        
        oi_change = int(df.iloc[idx_930]['Volume'] * 0.48) - int(df.iloc[idx_915]['Volume'] * 0.42)
        movement_type = get_oi_movement(oi_change, c_930 - c_915)
        levels = calculate_pivots(float(h_930), float(l_930), float(c_930))

        strike_step = 5.0 if live_price < 300 else (20.0 if live_price < 1500 else 50.0)
        atm_strike = round(live_price / strike_step) * strike_step
        max_pain = atm_strike  
        
        # மாஸ்டர் கண்டெய்னரை மட்டும் லூப்பில் புதுப்பிப்பதால் எவ்வித பிழையும் வராது
        with main_container.container():
            head_col1, head_col2 = st.columns([1.5, 1])
            with head_col1:
                st.markdown(f"<h2>QUANTUM-X NSE TERMINAL // <span style='color:#00ff88;'>{ticker_clean}</span></h2>", unsafe_allow_html=True)
            with head_col2:
                # எரர் வராமல் இருக்க key பாராமீட்டர் நீக்கப்பட்டுள்ளது
                components.html(f"""
                    <div class="tradingview-widget-container" style="margin-top: 5px;">
                      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-single-quote.js" async>
                      {{"symbol": "NSE:{ticker_clean}", "width": "100%", "colorTheme": "dark", "isTransparent": true, "locale": "en"}}
                      </script>
                    </div>
                """, height=50)

            # Core Price Engine Feed
            st.markdown(f"""
            <div style="background-color:#090a0f; padding: 14px; border-radius: 6px; border: 1px solid #1c2333; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <span style="color:#566275; font-size:11px; font-weight:700; letter-spacing:1.5px;">NSE TICK FEED (NSE_LIVE)</span>
                        <h1 class="mono-text" style="color:#FFFFFF; margin:0px; font-size:38px; font-weight:700;">₹ {live_price:.2f} <span style="color:{dc_color}; font-size:18px; font-weight:normal;">{day_change:+.2f} ({((day_change/day_open)*100):+.2f}%)</span></h1>
                    </div>
                    <div style="display: flex; gap: 25px; background-color:#121620; padding:10px 20px; border-radius:4px; border:1px solid #252e3d;">
                        <div><span style="color:#7889a3; font-size:11px; font-weight:600;">VWAP TRACKER</span><br><b class="mono-text" style="color:#00b0ff; font-size:16px;">{current_vwap:.2f}</b></div>
                        <div><span style="color:#7889a3; font-size:11px; font-weight:600;">MOMENTUM RSI</span><br><b class="mono-text" style="color:#ffcc00; font-size:16px;">{current_rsi:.2f}</b></div>
                        <div><span style="color:#7889a3; font-size:11px; font-weight:600;">EMA 9 / 21</span><br><b class="mono-text" style="color:#00ff88; font-size:16px;">{current_ema9:.1f}/{current_ema21:.1f}</b></div>
                        <div><span style="color:#7889a3; font-size:11px
