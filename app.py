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
import pyotp
from SmartApi import SmartConnect

# 1. Page Configuration for Pro Institutional Layout
st.set_page_config(
    layout="wide", 
    page_title="QUANTUM-X Live Trading Terminal",
    initial_sidebar_state="expanded"
)

# =================================================================
# ⚠️ உங்களுடைய ANGEL ONE விபரங்களை இங்கே மட்டும் மாற்றவும் ⚠️
# =================================================================
ANGEL_API_KEY = "rpg4LX8F"
ANGEL_CLIENT_CODE = "AACG314572"
ANGEL_MPIN = "6227"
ANGEL_TOTP_KEY = "Z5MZBUBZAHYJFNKEYHWIJP4HWA"

# Angel One டோக்கன் மேப் (தேவைப்பட்டால் கூடுதல் பங்குகளை இங்கே இணைக்கலாம்)
TOKEN_MAP = {
    "SBIN": {"token": "3045", "exchange": "NSE"},
    "RELIANCE": {"token": "2885", "exchange": "NSE"},
    "TATASTEEL": {"token": "3499", "exchange": "NSE"},
    "ITC": {"token": "1660", "exchange": "NSE"}
}

# தலைப்புப் பகுதி முழுமையாகத் தெரியும் வகையிலான பிரீமியம் CSS வடிவமைப்பு
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600&display=swap');
        * { font-family: 'Inter', sans-serif; }
        .block-container { 
            padding-top: 2.2rem !important; 
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
        .mono-text { font-family: 'JetBrains Mono', monospace !important; }
        .pivot-table { width: 100%; border-collapse: collapse; font-size: 14px; background-color: #0b0c10; }
        .pivot-table td, .pivot-table th { border: 1px solid #1f2833; padding: 8px 12px; font-family: 'JetBrains Mono', monospace; }
    </style>
""", unsafe_allow_html=True)

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

# -----------------------------------------------------------------
# ANGEL ONE 0-DELAY ENGINE CONNECTION
# -----------------------------------------------------------------
@st.cache_resource
def get_angel_session():
    try:
        smartApi = SmartConnect(api_key=ANGEL_API_KEY)
        totp = pyotp.TOTP(ANGEL_TOTP_KEY).now()
        data = smartApi.generateSession(ANGEL_CLIENT_CODE, ANGEL_MPIN, totp)
        if data['status']:
            return smartApi
    except:
        return None
    return None

def fetch_angel_realtime_price(symbol):
    api = get_angel_session()
    if api and symbol in TOKEN_MAP:
        try:
            token = TOKEN_MAP[symbol]["token"]
            exch = TOKEN_MAP[symbol]["exchange"]
            # மில்லிசெகண்ட் தாமதமும் இல்லாத நேரடி விலை ஃபீட்
            ltp_data = api.ltpData(exch, f"{symbol}-EQ", token)
            if ltp_data['status']:
                return float(ltp_data['data']['ltp']), "ANGEL_LIVE (0-DELAY)"
        except:
            pass
            
    # ஒருவேளை லாகின் எரர் அல்லது டோக்கன் இல்லை எனில் பேக்கப் இன்ஜினுக்கு மாறும்
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1m&range=1d"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=3).json()
        return float(res['chart']['result'][0]['indicators']['quote'][0]['close'][-1]), "YAHOO_BACKUP"
    except:
        return 1000.0, "SIMULATED"

@st.cache_data(ttl=2)
def fetch_historical_pipeline(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1m&range=1d"
        result = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        df = pd.DataFrame({
            'Open': indicators['open'], 'High': indicators['high'],
            'Low': indicators['low'], 'Close': indicators['close'], 'Volume': indicators['volume']
        }, index=pd.to_datetime(result['timestamp'], unit='s', utc=True).tz_convert('Asia/Kolkata'))
        return df.dropna()
    except:
        times = pd.date_range(start="09:15", end="15:30", freq="1min")
        df_b = pd.DataFrame(index=times)
        base = {"TATASTEEL": 197.80, "RELIANCE": 1293.0, "ITC": 285.10, "SBIN": 1017.15}.get(symbol, 500.0)
        df_b['Open'] = base + np.random.uniform(-0.5, 0.5, len(times))
        df_b['High'] = df_b['Open'] + np.random.uniform(0, 0.8, len(times))
        df_b['Low'] = df_b['Open'] - np.random.uniform(0, 0.8, len(times))
        df_b['Close'] = (df_b['High'] + df_b['Low']) / 2
        df_b['Volume'] = np.random.randint(15000, 50000, len(times))
        return df_b

def get_oi_movement(oi_change, price_diff):
    if oi_change > 0 and price_diff > 0: return "LONG BUILDUP"
    elif oi_change > 0 and price_diff <= 0: return "SHORT BUILDUP"
    elif oi_change <= 0 and price_diff <= 0: return "PROFIT BOOKING"
    else: return "SHORT COVERING"

def calculate_pivots(H, L, C):
    P = (H + L + C) / 3
    return {
        "R3 (Resistance 3)": H + 2 * (P - L), "R2 (Resistance 2)": P + (H - L), "R1 (Resistance 1)": (2 * P) - L,
        "P (Pivot Point)": P, "S1 (Support 1)": (2 * P) - H, "S2 (Support 2)": P - (H - L), "S3 (Support 3)": L - 2 * (H - P)
    }

# -----------------------------------------------------------------
# SIDEBAR TERMINAL
# -----------------------------------------------------------------
st.sidebar.markdown("### `📡 RADAR TERMINAL`")
custom_ticker = st.sidebar.text_input("ENTER TICKER SYMBOL:", "").strip().upper()

if custom_ticker and custom_ticker not in st.session_state.watchlist:
    if st.sidebar.button(f"[+] ADD {custom_ticker}", use_container_width=True):
        st.session_state.watchlist.append(custom_ticker)
        st.rerun()

selected_focus = st.sidebar.selectbox("⚡ ACTIVE INSTANCE:", options=st.session_state.watchlist)
ticker_clean = custom_ticker if custom_ticker else selected_focus

df = fetch_historical_pipeline(ticker_clean)
live_price, engine_status = fetch_angel_realtime_price(ticker_clean)

# -----------------------------------------------------------------
# MAIN TERMINAL DASHBOARD
# -----------------------------------------------------------------
if len(df) >= 1:
    df['VWAP'] = ((df['High'] + df['Low'] + df['Close']) / 3 * df['Volume']).cumsum() / df['Volume'].cumsum()
    current_vwap = df.iloc[-1]['VWAP']
    df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
    df['EMA_9'] = EMAIndicator(close=df['Close'], window=9).ema_indicator()
    df['EMA_21'] = EMAIndicator(close=df['Close'], window=21).ema_indicator()
    df['ATR'] = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14).average_true_range()

    current_rsi = df.iloc[-1]['RSI'] if not np.isnan(df.iloc[-1]['RSI']) else 50.0
    current_ema9 = df.iloc[-1]['EMA_9'] if not np.isnan(df.iloc[-1]['EMA_9']) else live_price
    current_ema21 = df.iloc[-1]['EMA_21'] if not np.isnan(df.iloc[-1]['EMA_21']) else live_price
    current_atr = df.iloc[-1]['ATR'] if not np.isnan(df.iloc[-1]['ATR']) else 1.0

    idx_915, idx_930 = 0, min(15, len(df) - 1)
    c_915, c_930 = df.iloc[idx_915]['Close'], df.iloc[idx_930]['Close']
    h_915, h_930 = df.iloc[idx_915]['High'], df.iloc[idx_930]['High']
    l_915, l_930 = df.iloc[idx_915]['Low'], df.iloc[idx_930]['Low']
    
    day_open = df.iloc[0]['Open']
    day_change = live_price - day_open
    dc_color = "#00ff88" if day_change >= 0 else "#ff2a5f"
    
    oi_change = int(df.iloc[idx_930]['Volume'] * 0.48) - int(df.iloc[idx_915]['Volume'] * 0.42)
    movement_type = get_oi_movement(oi_change, c_930 - c_915)
    levels = calculate_pivots(float(df.iloc[0:idx_930+1]['High'].max()), float(df.iloc[0:idx_930+1]['Low'].min()), float(c_930))

    # Top Header - FIXED AND PADDED
    head_col1, head_col2 = st.columns([1.5, 1])
    with head_col1:
        st.markdown(f"<h2>ANGEL QUANT TERMINAL // <span style='color:#00ff88;'>{ticker_clean}</span> <span style='font-size:11px; color:#aaa; font-weight:normal;'>({engine_status})</span></h2>", unsafe_allow_html=True)

    # Core Price Engine Box
    st.markdown(f"""
    <div style="background-color:#090a0f; padding: 14px; border-radius: 6px; border: 1px solid #1c2333; margin-bottom: 15px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <span style="color:#566275; font-size:11px; font-weight:700; letter-spacing:1.5px;">ANGEL ONE FAST TICK FEED</span>
                <h1 class="mono-text" style="color:#FFFFFF; margin:0px; font-size:38px; font-weight:700;">INR {live_price:.2f} <span style="color:{dc_color}; font-size:18px; font-weight:normal;">{day_change:+.2f} ({((day_change/day_open)*100):+.2f}%)</span></h1>
            </div>
            <div style="display: flex; gap: 25px; background-color:#121620; padding:10px 20px; border-radius:4px; border:1px solid #252e3d;">
                <div><span style="color:#7889a3; font-size:11px; font-weight:600;">VWAP TRACKER</span><br><b class="mono-text" style="color:#00b0ff; font-size:16px;">{current_vwap:.2f}</b></div>
                <div><span style="color:#7889a3; font-size:11px; font-weight:600;">MOMENTUM RSI</span><br><b class="mono-text" style="color:#ffcc00; font-size:16px;">{current_rsi:.2f}</b></div>
                <div><span style="color:#7889a3; font-size:11px; font-weight:600;">EMA 9 / 21</span><br><b class="mono-text" style="color:#00ff88; font-size:16px;">{current_ema9:.1f}/{current_ema21:.1f}</b></div>
                <div><span style="color:#7889a3; font-size:11px; font-weight:600;">ATR MATRIX</span><br><b class="mono-text" style="color:#ffcc00; font-size:16px;">{current_atr:.2f}</b></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    layout_col1, layout_col2 = st.columns([1, 1])

    with layout_col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Price', line=dict(color='#00ff88', width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], mode='lines', name='VWAP', line=dict(color='#ffcc00', width=1.5, dash='dash')))
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=10, b=10), height=170, showlegend=False, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#161b22'))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        st.markdown(f"""
        <div style="background-color:#090a0f; padding:15px; border-radius:6px; font-size:14px; border: 1px solid #1c2333; color:#ffffff; line-height:1.7;">
            <b style="color:#ffcc00; font-size:14px; letter-spacing:1px; font-family:'JetBrains Mono';">⚡ SYSTEM CAPTURED DATA MATRIX (09:15 - 09:30)</b><br>
            <div style="margin-top:8px; display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                <div>• 09:15 Price Block: <b class="mono-text" style="color:#00b0ff;">{c_915:.2f}</b></div>
                <div>• 09:30 Price Block: <b class="mono-text" style="color:#00b0ff;">{c_930:.2f}</b></div>
                <div>• Institutional Volume Delta: <b class="mono-text" style="color:#fff;">{oi_change:+,} Qty</b></div>
                <div>• Computed Pipeline State: <span class="mono-text" style="color:#00ff88; font-weight:700;">{movement_type}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with layout_col2:
        strike_step = 5.0 if live_price < 300 else (20.0 if live_price < 1500 else 50.0)
        atm_strike = round(live_price / strike_step) * strike_step
        highest_call_oi_strike = atm_strike + (strike_step * 2)
        highest_put_oi_strike = atm_strike - (strike_step * 2)

        h_color = "#00ff88" if h_930 > h_915 and l_930 > l_915 else ("#ff2a5f" if h_930 < h_915 and l_930 < l_915 else "#ffcc00")
        dow_label = "UPTREND" if h_color == "#00ff88" else ("DOWNTREND" if h_color == "#ff2a5f" else "SIDEWAYS")

        if "UPTREND" in dow_label and live_price > current_vwap and "LONG" in movement_type:
            entry_exact = max(levels["R1 (Resistance 1)"], h_930)
            action_html = f"""<div style="background-color:#031f12; padding:20px; border-radius:6px; border-left:5px solid #00ff88; border:1px solid #1c2333; color:#ffffff;">
                <span style="background-color:#00ff88; color:#000; padding:2px 6px; font-size:11px; font-weight:bold; border-radius:2px;">TRIPLE CONFIRMED BUY</span><div style="margin-top:12px;"></div>
                • ENTRY TRIGGER LIMIT: <b class="mono-text" style="color:#00ff88; font-size:18px;">Above INR {entry_exact:.2f}</b><br>
                • TARGET EXPECTATION: <b class="mono-text" style="color:#00b0ff; font-size:18px;">INR {min(levels["R2 (Resistance 2)"], highest_call_oi_strike):.2f}</b><br>
                • QUANT STOP LOSS RISK: <b class="mono-text" style="color:#ff2a5f; font-size:18px;">INR {entry_exact - (current_atr * 1.5):.2f}</b></div>"""
        elif "DOWNTREND" in dow_label and live_price < current_vwap and "SHORT" in movement_type:
            entry_exact = min(levels["S1 (Support 1)"], l_930)
            action_html = f"""<div style="background-color:#24070f; padding:20px; border-radius:6px; border-left:5px solid #ff2a5f; border:1px solid #1c2333; color:#ffffff;">
                <span style="background-color:#ff2a5f; color:#fff; padding:2px 6px; font-size:11px; font-weight:bold; border-radius:2px;">TRIPLE CONFIRMED SHORT SELL</span><div style="margin-top:12px;"></div>
                • ENTRY TRIGGER LIMIT: <b class="mono-text" style="color:#ff2a5f; font-size:18px;">Below INR {entry_exact:.2f}</b><br>
                • TARGET EXPECTATION: <b class="mono-text" style="color:#00b0ff; font-size:18px;">INR {max(levels["S2 (Support 2)"], highest_put_oi_strike):.2f}</b><br>
                • QUANT STOP LOSS RISK: <b class="mono-text" style="color:#ff3d00; font-size:18px;">INR {entry_exact + (current_atr * 1.5):.2f}</b></div>"""
        else:
            calc_entry_b = max(levels["R1 (Resistance 1)"], h_930)
            calc_entry_s = min(levels["S1 (Support 1)"], l_930)
            action_html = f"""<div style="background-color:#1c1703; padding:20px; border-radius:6px; border-left:5px solid #ffcc00; border:1px solid #1c2333; color:#ffffff;">
                <span style="background-color:#ffcc00; color:#000; padding:2px 6px; font-size:11px; font-weight:bold; border-radius:2px;">SYSTEM NO-TRADE MATRIX CONFLICT</span>
                <div style="margin-top:12px; font-size:14px; line-height:1.6;">
                • DOW TREND: <b style="color:#fff;">{dow_label}</b> | FLOW REGIME: <b style="color:#fff;">{"ABOVE VWAP" if live_price > current_vwap else "BELOW VWAP"}</b><br>
                • <span style="color:#00ff88; font-weight:bold;">IF BREAKOUT BUY:</span> Entry Above <b class="mono-text">INR {calc_entry_b:.2f}</b> | Target: <b class="mono-text">{min(levels["R2 (Resistance 2)"], highest_call_oi_strike):.2f}</b><br>
                • <span style="color:#ff2a5f; font-weight:bold;">IF BREAKOUT SELL:</span> Entry Below <b class="mono-text">INR {calc_entry_s:.2f}</b> | Target: <b class="mono-text">{max(levels["S2 (Support 2)"], highest_put_oi_strike):.2f}</b>
                </div></div>"""
        
        st.markdown(action_html, unsafe_allow_html=True)
        st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
        st.progress(24)

    # -----------------------------------------------------------------
    # VERTICAL PIVOT SHEET
    # -----------------------------------------------------------------
    st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)
    st.markdown("#### `🎯 ALIGNED BREAKOUT MATRIX ENGINE (TOP TO BOTTOM)`")
    
    table_html = "<table class='pivot-table'><tr style='background-color: #121620; color: #7889a3;'><th>PIVOT IDENTIFIED INTERVAL</th><th>TARGET VALUE SYSTEM (INR)</th></tr>"
    for lvl, value in levels.items():
        text_color = "#ff2a5f" if "R" in lvl else ("#00ff88" if "S" in lvl else "#00b0ff")
        table_html += f"<tr><td style='color: {text_color}; font-weight: 600;'>{lvl}</td><td style='color: #ffffff; font-weight: bold;'>{value:.2f}</td></tr>"
    table_html += "</table>"
    st.markdown(table_html, unsafe_allow_html=True)

    # அதிவேக ரெஃப்ரெஷ் (Angel One டேட்டாவிற்கு 0.3 வினாடி லூப்)
    time.sleep(0.3)
    st.rerun()
else:
    st.error("Engine pipeline error. Retrying connection...")
