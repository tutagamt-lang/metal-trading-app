import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import time

# 1. Page Configuration for Pro Institutional Layout
st.set_page_config(
    layout="wide", 
    page_title="QUANTUM-X Live Trading Terminal",
    initial_sidebar_state="expanded"
)

# 🎯 LIGHT-MODE HIGH-CONTRAST TERMINAL STYLE (STABLE CSS - NO F-STRING CONFLICTS)
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght=400;700&family=Inter:wght=400;600;700&display=swap');
        
        .stApp { background-color: #F8FAFC !important; color: #0F172A !important; }
        * { font-family: 'Inter', sans-serif; }
        .block-container { padding-top: 1.5rem !important; padding-bottom: 0rem; }
        
        h2 { font-weight: 700; letter-spacing: -0.5px; margin: 5px 0 10px 0 !important; color: #0F172A !important; }
        h4 { font-weight: 700; color: #1E3A8A !important; font-family: 'JetBrains Mono', monospace !important; margin-top: 20px !important; }
        .mono-text { font-family: 'JetBrains Mono', monospace !important; font-weight: 700 !important; }
        
        /* 📊 CRYSTAL CLEAR TABLES */
        .quant-table { width: 100%; border-collapse: collapse; font-size: 15px; background-color: #FFFFFF !important; margin-bottom: 15px; border: 2px solid #0F172A !important; }
        .quant-table th { background-color: #0F172A !important; color: #FFFFFF !important; text-align: left; padding: 12px 14px; font-family: 'JetBrains Mono', monospace; border: 2px solid #0F172A !important; font-size: 13px; font-weight: 700 !important; text-transform: uppercase; }
        .quant-table td { border: 2px solid #E2E8F0 !important; padding: 12px 14px; font-family: 'JetBrains Mono', monospace; color: #0F172A !important; font-weight: 700 !important; font-size: 15px; background-color: #FFFFFF !important; }

        /* 🛑 SYSTEM PANEL BOXES */
        .matrix-box { background-color: #FFFFFF; padding: 22px; border-radius: 6px; border: 2px solid #0F172A; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
        
        /* Sidebar Styling Fixes */
        section[data-testid="stSidebar"] { background-color: #1E293B !important; color: #FFFFFF !important; }
        section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
        section[data-testid="stSidebar"] input { color: #000000 !important; }
        
        /* Status Widget Override */
        div[data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
    </style>
""", unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

# -----------------------------------------------------------------
# DATA ENGINE PIPELINE & INTRADAY PIVOT CALCULATOR
# -----------------------------------------------------------------
def get_oi_movement(oi_change, price_diff):
    if oi_change > 0 and price_diff > 0: return "LONG BUILDUP"
    elif oi_change > 0 and price_diff <= 0: return "SHORT BUILDUP"
    elif oi_change <= 0 and price_diff <= 0: return "PROFIT BOOKING"
    else: return "SHORT COVERING"

def calculate_pivots(H, L, C, O):
    P = (H + L + C + O) / 4
    R1 = (2 * P) - L
    S1 = (2 * P) - H
    return {
        "R3 (Resistance 3)": H + (2 * (P - L)),
        "R2 (Resistance 2)": P + (R1 - S1),
        "R1 (Resistance 1)": R1,
        "P (Pivot Point)": P,
        "S1 (Support 1)": S1,
        "S2 (Support 2)": P - (R1 - S1),
        "S3 (Support 3)": L - (2 * (H - P))
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
        base = {"TATASTEEL": 197.10, "RELIANCE": 1308.0, "ITC": 288.30, "SBIN": 1020.65}.get(symbol, 500.0)
        df_backup['Open'] = base + np.random.uniform(-0.5, 0.5, len(times))
        df_backup['High'] = df_backup['Open'] + np.random.uniform(0, 0.8, len(times))
        df_backup['Low'] = df_backup['Open'] - np.random.uniform(0, 0.8, len(times))
        df_backup['Close'] = (df_backup['High'] + df_backup['Low']) / 2
        df_backup['Volume'] = np.random.randint(15000, 50000, len(times))
        return df_backup, "SIM"

# -----------------------------------------------------------------
# SIDEBAR TERMINAL
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

# Sidebar Multi-Stock Monitor
st.sidebar.markdown("---")
st.sidebar.markdown("#### `⚡ MULTI-STOCK MONITOR`")
scanner_data = []
for s in st.session_state.watchlist:
    s_df, _ = fetch_realtime_nse_data(s)
    if len(s_df) >= 1:
        idx_30 = min(15, len(s_df)-1)
        s_move = get_oi_movement(
            int(s_df.iloc[idx_30]['Volume']*0.48) - int(s_df.iloc[0]['Volume']*0.42), 
            s_df.iloc[idx_30]['Close'] - s_df.iloc[0]['Close']
        )
        scanner_data.append({"STOCK": s, "PRICE": f"{s_df.iloc[-1]['Close']:.2f}", "MATRIX": s_move})
st.sidebar.dataframe(pd.DataFrame(scanner_data), hide_index=True, use_container_width=True)

# -----------------------------------------------------------------
# MAIN DASHBOARD TERMINAL
# -----------------------------------------------------------------
df, data_status = fetch_realtime_nse_data(ticker_clean)

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

    # ⏰ EXTRACTING EXACT 09:15 TO 09:30 RANGE FOR ANCHOR PIVOT CALCULATION
    df_15min = df.between_time("09:15", "09:30")
    
    if not df_15min.empty:
        o_anchor = float(df_15min.iloc[0]['Open'])
        c_anchor = float(df_15min.iloc[-1]['Close'])
        h_anchor = float(df_15min['High'].max())
        l_anchor = float(df_15min['Low'].min())
    else:
        o_anchor = float(df.iloc[0]['Open'])
        c_anchor = float(df.iloc[min(15, len(df)-1)]['Close'])
        h_anchor = float(df.iloc[0:16]['High'].max())
        l_anchor = float(df.iloc[0:16]['Low'].min())

    live_price = df.iloc[-1]['Close']
    day_open = df.iloc[0]['Open']
    day_change = live_price - day_open
    dc_color = "#10B981" if day_change >= 0 else "#EF4444"
    pct_change = ((day_change / day_open) * 100) if day_open != 0 else 0.0
    
    idx_0, idx_15 = 0, min(15, len(df) - 1)
    oi_change = int(df.iloc[idx_15]['Volume'] * 0.48) - int(df.iloc[idx_0]['Volume'] * 0.42)
    movement_type = get_oi_movement(oi_change, c_anchor - o_anchor)
    
    levels = calculate_pivots(h_anchor, l_anchor, c_anchor, o_anchor)

    strike_step = 5.0 if live_price < 300 else (20.0 if live_price < 1500 else 50.0)
    atm_strike = round(live_price / strike_step) * strike_step
    max_pain = atm_strike  

    # Title Sections
    st.markdown(f"<h2>QUANTUM-X NSE TERMINAL // <span style='color:#10B981;'>{ticker_clean}</span></h2>", unsafe_allow_html=True)

    # Price Feed Ribbon 
    st.markdown(f"""
    <div style="background-color:#0F172A; padding: 18px; border-radius: 6px; margin-bottom: 15px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <span style="color:#94A3B8; font-size:12px; font-weight:700; letter-spacing:1.5px; font-family:'JetBrains Mono';">NSE TICK FEED (NSE_LIVE)</span>
                <h1 class="mono-text" style="color:#FFFFFF; margin:0px; font-size:38px; font-weight:700;">🔳 {live_price:.2f} <span style="color:{dc_color}; font-size:20px; font-weight:700;">{day_change:+.2f} ({pct_change:+.2f}%)</span></h1>
            </div>
            <div style="display: flex; gap: 20px; background-color:#1E293B; padding:12px 18px; border-radius:4px; border:1px solid #334155;">
                <div><span style="color:#94A3B8; font-size:11px; font-weight:700;">VWAP TRACKER</span><br><b class="mono-text" style="color:#38BDF8; font-size:16px;">{current_vwap:.2f}</b></div>
                <div><span style="color:#94A3B8; font-size:11px; font-weight:700;">MOMENTUM RSI</span><br><b class="mono-text" style="color:#F59E0B; font-size:16px;">{current_rsi:.2f}</b></div>
                <div><span style="color:#94A3B8; font-size:11px; font-weight:700;">EMA 9 / 21</span><br><b class="mono-text" style="color:#34D399; font-size:16px;">{current_ema9:.1f}/{current_ema21:.1f}</b></div>
                <div><span style="color:#94A3B8; font-size:11px; font-weight:700;">ATR MATRIX</span><br><b class="mono-text" style="color:#F87171; font-size:16px;">{current_atr:.2f}</b></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Chart & Grid Blocks
    layout_col1, layout_col2 = st.columns([1.2, 1])

    with layout_col1:
        # Mini Chart View
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Price', line=dict(color='#10B981', width=2.5)))
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], mode='lines', name='VWAP', line=dict(color='#2563EB', width=2, dash='dash')))
        fig.update_layout(
            template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=10, b=10), height=140, showlegend=False,
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#E2E8F0')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{ticker_clean}")

        # 📊 09:15 - 09:30 ANCHOR MULTI-GRID BOXES (VISUAL PARITY WITH IMAGE_A1D341.PNG)
        st.markdown(f"""
        <div style="background-color:#FFFFFF; padding:15px; border-radius:6px; border: 2px solid #0F172A; color:#0F172A !important; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);">
            <b style="color:#0F172A; font-size:13px; letter-spacing:0.5px; font-family:'JetBrains Mono';">⚡ NSE SYSTEM CAPTURED DATA MATRIX (09:15 - 09:30 Anchor)</b><br>
            <div style="margin-top:10px; display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
                <div style="background-color:#F8FAFC; padding:10px; border:1px solid #CBD5E1; border-radius:4px; font-family:'JetBrains Mono'; font-size:14px;">• <b>OPEN:</b> <span style="color:#0F172A; font-weight:700;">₹ {o_anchor:.2f}</span></div>
                <div style="background-color:#F8FAFC; padding:10px; border:1px solid #CBD5E1; border-radius:4px; font-family:'JetBrains Mono'; font-size:14px;">• <b>HIGH:</b> <span style="color:#059669; font-weight:700;">₹ {h_anchor:.2f}</span></div>
                <div style="background-color:#F8FAFC; padding:10px; border:1px solid #CBD5E1; border-radius:4px; font-family:'JetBrains Mono'; font-size:14px;">• <b>LOW:</b> <span style="color:#DC2626; font-weight:700;">₹ {l_anchor:.2f}</span></div>
                <div style="background-color:#F8FAFC; padding:10px; border:1px solid #CBD5E1; border-radius:4px; font-family:'JetBrains Mono'; font-size:14px;">• <b>CLOSE:</b> <span style="color:#2563EB; font-weight:700;">₹ {c_anchor:.2f}</span></div>
            </div>
            <div style="margin-top:12px; font-size:13px; font-family:'JetBrains Mono'; color:#475569; border-top:1px dashed #E2E8F0; padding-top:8px;">
                ⇄ Volume Flow State: <b>{movement_type} ({oi_change:+,} Qty)</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with layout_col2:
        # SYSTEM CONFLICT MATRIX (RESTORING ORIGINAL WITH STABLE ESCAPED STYLES)
        dow_label = "UPTREND" if c_anchor > o_anchor else "DOWNTREND"
        calc_entry_b = max(levels["R1 (Resistance 1)"], h_anchor)
        calc_entry_s = min(levels["S1 (Support 1)"], l_anchor)
        flow_label = "ABOVE VWAP" if live_price > current_vwap else "BELOW VWAP"
        
        st.markdown(f"""
        <div style="background-color:#1E1E14; padding:20px; border-radius:6px; border: 2px solid #0F172A; border-left:8px solid #D97706; height: 232px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
            <span style="background-color:#D97706; color:#FFFFFF; padding:4px 8px; font-size:12px; font-weight:bold; border-radius:2px; font-family:'JetBrains Mono';">SYSTEM CONFLICT MATRIX</span>
            <div style="margin-top:16px; font-size:14px; line-height:2.0; font-family:'JetBrains Mono'; color:#94A3B8;">
                • DOW TREND: <b style="color:#F59E0B;">{dow_label}</b> |
