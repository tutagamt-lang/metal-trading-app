import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from datetime import datetime
import pyotp
import time

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="QUANTUM-X Live Trading Terminal")

try:
    from SmartApi import SmartConnect
except ImportError:
    st.error("தயவுசெய்து உங்கள் requirements.txt கோப்பில் 'smartapi-python' சேர்க்கவும்.")

# 🎯 LIGHT-MODE HIGH-CONTRAST TERMINAL STYLE
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght=400;700&family=Inter:wght=400;600;700&display=swap');
        .stApp { background-color: #F8FAFC !important; color: #0F172A !important; }
        * { font-family: 'Inter', sans-serif; }
        .block-container { padding-top: 1.5rem !important; padding-bottom: 0rem; }
        h2 { font-weight: 700; letter-spacing: -0.5px; margin: 5px 0 10px 0 !important; color: #0F172A !important; }
        .mono-text { font-family: 'JetBrains Mono', monospace !important; font-weight: 700 !important; }
        .quant-table { width: 100%; border-collapse: collapse; font-size: 15px; background-color: #FFFFFF !important; margin-bottom: 15px; border: 2px solid #0F172A !important; }
        .quant-table th { background-color: #0F172A !important; color: #FFFFFF !important; text-align: left; padding: 12px 14px; font-family: 'JetBrains Mono', monospace; border: 2px solid #0F172A !important; font-size: 13px; font-weight: 700 !important; }
        .quant-table td { border: 2px solid #E2E8F0 !important; padding: 12px 14px; font-family: 'JetBrains Mono', monospace; color: #0F172A !important; font-weight: 700 !important; font-size: 15px; background-color: #FFFFFF !important; }
        section[data-testid="stSidebar"] { background-color: #1E293B !important; color: #FFFFFF !important; }
        section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
        section[data-testid="stSidebar"] input { color: #000000 !important; }
    </style>
""", unsafe_allow_html=True)

# 🔐 ANGELONE API CREDENTIALS AUTOMATIC CONFIGURATION
ANGEL_API_KEY = "rpg4LX8F"
ANGEL_CLIENT_ID = "AACG314572"
ANGEL_PASSWORD = "6227"
ANGEL_TOTP_KEY = "Z5MZBUBZAHYJFNKEYHWIJP4HWA"

try:
    calculated_totp = pyotp.TOTP(ANGEL_TOTP_KEY.strip()).now()
except Exception:
    calculated_totp = ""

st.sidebar.markdown("### `🔐 ANGELONE SMARTAPI API INTEGRATION`")
api_key = st.sidebar.text_input("ANGELONE API KEY:", value=ANGEL_API_KEY, type="password")
client_id = st.sidebar.text_input("CLIENT ID (e.g., S12345):", value=ANGEL_CLIENT_ID)
password = st.sidebar.text_input("PIN/PASSWORD:", value=ANGEL_PASSWORD, type="password")
totp_token = st.sidebar.text_input("TOTP TOKEN (Authenticator):", value=calculated_totp, type="password")

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

# 🎯 துல்லியமான நேரடி NSE CASH மார்க்கெட் டோக்கன்கள்
TOKEN_MAP = {
    "TATASTEEL": "3496", 
    "RELIANCE": "2885", 
    "ITC": "1660", 
    "SBIN": "3045"
}

def get_oi_movement(oi_change, price_diff):
    if oi_change > 0 and price_diff > 0: return "LONG BUILDUP"
    elif oi_change > 0 and price_diff <= 0: return "SHORT BUILDUP"
    elif oi_change <= 0 and price_diff <= 0: return "PROFIT BOOKING"
    else: return "SHORT COVERING"

def calculate_pivots(H, L, C, O):
    P = (H + C + L + O) / 4
    R1 = (2 * P) - L
    S1 = (2 * P) - H
    return {
        "R3": H + 2 * (P - L), "R2": P + (R1 - S1), "R1": R1,
        "P": P, "S1": S1, "S2": P - (R1 - S1), "S3": L - 2 * (H - P)
    }

@st.cache_data(ttl=1)
def fetch_realtime_nse_data(symbol, _api_key, _client_id, _password, _totp):
    try:
        smart_conn = SmartConnect(api_key=_api_key)
        smart_conn.generateSession(_client_id, _password, _totp)
        
        token = TOKEN_MAP.get(symbol, "3496")
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        historic_param = {
            "exchange": "NSE", 
            "symboltoken": token, 
            "interval": "ONE_MINUTE",
            "fromdate": f"{current_date} 09:15", 
            "todate": f"{current_date} 15:30"
        }
        response = smart_conn.getCandleData(historic_param)
        
        if response and response.get("status") and response.get("data"):
            candles = response["data"]
            df_api = pd.DataFrame(candles, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df_api['OI'] = df_api['Volume'] * 2
            df_api['Timestamp'] = pd.to_datetime(df_api['Timestamp']).dt.tz_localize('Asia/Kolkata')
            df_api.set_index('Timestamp', inplace=True)
            return df_api, "LIVE_ANGELONE"
        else:
            st.error("உங்களது கணக்கில் இந்த பங்கிற்கான லைவ் டேட்டா ஃபீட் இன்னும் வரவில்லை. மார்க்கெட் நேரத்தில் முயற்சிக்கவும்.")
            st.stop()
            
    except Exception as e:
        st.error(f"கணினி பிழை (Exception): {str(e)}")
        st.stop()

st.sidebar.markdown("---")
selected_focus = st.sidebar.selectbox("⚡ ACTIVE INSTANCE:", options=st.session_state.watchlist)

df, data_status = fetch_realtime_nse_data(selected_focus, api_key, client_id, password, totp_token)

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

    df_15min = df[(df.index.hour == 9) & (df.index.minute >= 15) & (df.index.minute <= 30)]
    
    if not df_15min.empty:
        matrix_open = float(df_15min.iloc[0]['Open'])               
        matrix_high = float(df_15min['High'].max())                 
        matrix_low = float(df_15min['Low'].min())                   
        matrix_close = float(df_15min.iloc[-1]['Close'])
        oi_915 = int(df_15min.iloc[0]['OI'])
        oi_930 = int(df_15min.iloc[-1]['OI'])
        oi_difference = oi_930 - oi_915
    else:
        matrix_open, matrix_high = float(df.iloc[0]['Open']), float(df.iloc[0]['High'])
        matrix_low, matrix_close = float(df.iloc[0]['Low']), float(df.iloc[0]['Close'])
        oi_915, oi_930, oi_difference = 100000, 120000, 2000

    live_price = float(df.iloc[-1]['Close'])
    day_open = float(df.iloc[0]['Open'])
    day_change = live_price - day_open
    dc_color = "#10B981" if day_change >= 0 else "#EF4444"
    pct_change = ((day_change / day_open) * 100) if day_open != 0 else 0.0
    
    movement_type = get_oi_movement(oi_difference, matrix_close - matrix_open)
    levels = calculate_pivots(matrix_high, matrix_low, matrix_close, matrix_open)

    st.markdown(f"<h2>QUANTUM-X NSE TERMINAL // <span style='color:#1E4A8A;'>{selected_focus}</span> <span style='font-size:12px;color:#94A3B8;'>DATA STATUS: {data_status}</span></h2>", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background-color:#FFFFFF; padding: 18px; border-radius: 6px; border: 2px solid #0F172A; margin-bottom: 15px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <span style="color:#475569; font-size:12px; font-weight:700; font-family:'JetBrains Mono';">NSE LIVE TICK FEED</span>
                <h1 class="mono-text" style="color:#0F172A; margin:0px; font-size:38px;">₹ {live_price:.2f} <span style="color:{dc_color}; font-size:20px;">{day_change:+.2f} ({pct_change:+.2f}%)</span></h1>
            </div>
            <div style="display: flex; gap: 20px; background-color:#F1F5F9; padding:12px 18px; border-radius:4px; border:2px solid #0F172A;">
                <div><span style="color:#475569; font-size:12px; font-weight:700;">VWAP TRACKER</span><br><b class="mono-text" style="color:#2563EB;">{current_vwap:.2f}</b></div>
                <div><span style="color:#475569; font-size:12px; font-weight:700;">MOMENTUM RSI</span><br><b class="mono-text" style="color:#D97706;">{current_rsi:.2f}</b></div>
                <div><span style="color:#475569; font-size:12px; font-weight:700;">EMA 9 / 21</span><br><b class="mono-text" style="color:#059669;">{current_ema9:.1f}/{current_ema21:.1f}</b></div>
                <div><span style="color:#475569; font-size:12px; font-weight:700;">ATR MATRIX</span><br><b class="mono-text" style="color:#DC2626;">{current_atr:.2f}</b></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    layout_col1, layout_col2 = st.columns([1, 1])

    with layout_col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color='#10B981', width=2.5)))
        fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=10, b=10), height=140, showlegend=False, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#E2E8F0'))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        st.markdown(f"""
        <div style="background-color:#FFFFFF; padding:15px; border-radius:6px; font-size:14px; border: 2px solid #0F172A; color:#0F172A !important; line-height:1.8;">
            <b style="color:#1E3A8A !important; font-size:13px; font-family:'JetBrains Mono';">⚡ NSE SYSTEM CAPTURED DATA MATRIX (09:15 - 09:30 RANGE)</b><br>
            <div style="margin-top:8px; display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                <div>• 15-Min Open Price: <b class="mono-text" style="color:#2563EB;">&#8377; {matrix_open:.2f}</b></div>
                <div>• 15-Min High Price: <b class="mono-text" style="color:#059669;">&#8377; {matrix_high:.2f}</b></div>
                <div>• 15-Min Low Price: <b class="mono-text" style="color:#DC2626;">&#8377; {matrix_low:.2f}</b></div>
                <div>• 15-Min Close Price: <b class="mono-text" style="color:#2563EB;">&#8377; {matrix_close:.2f}</b></div>
                <div style="grid-column: span 2; border-top: 1px dashed #CBD5E1; margin-top: 5px; padding-top: 5px;"></div>
                <div>• 🚀 Volume @ 09:15: <b class="mono-text" style="color:#475569;">{oi_915:,}</b></div>
                <div>• 🏁 Volume @ 09:30: <b class="mono-text" style="color:#475569;">{oi_930:,}</b></div>
                <div>• 📊 Vol Change (Delta): <b class="mono-text" style="color:#2563EB;">{oi_difference:+,}</b></div>
                <div>• 🎯 Flow State: <span class="mono-text" style="color:#D97706; font-weight:bold;">{movement_type}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with layout_col2:
        h_color = "#059669" if matrix_close > matrix_open else "#DC2626"
        dow_label = "UPTREND" if h_color == "#059669" else "DOWNTREND"
        calc_entry_b = max(levels["R1"], matrix_high)
        calc_entry_s = min(levels["S1"], matrix_low)
        flow_label = "ABOVE VWAP" if live_price > current_vwap else "BELOW VWAP"
        
        st.markdown(f"""
        <div style="background-color:#FFFFFF; padding:18px; border-radius:6px; border: 2px solid #0F172A; border-left:8px solid #D97706; height: 260px;">
            <span style="background-color:#D97706; color:#FFFFFF; padding:4px 8px; font-size:12px; font-weight:bold; font-family:'JetBrains Mono';">SYSTEM CONFLICT MATRIX</span>
            <div style="margin-top:12px; font-size:14px; line-height:1.8; font-family:'JetBrains Mono';">
                • DOW TREND: <b style="color:#B45309;">{dow_label}</b> | FLOW: <b style="color:#DC2626;">{flow_label}</b><br>
                • <span style="color:#059669; font-weight:bold;">IF BREAKOUT BUY:</span> Entry Above <b class="mono-text">&#8377; {calc_entry_b:.2f}</b><br>
                • <span style="color:#DC2626; font-weight:bold;">IF BREAKOUT SELL:</span> Entry Below <b class="mono-text">&#8377; {calc_entry_s:.2f}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("#### `🎯 ALIGNED BREAKOUT MATRIX ENGINE (TOP TO BOTTOM)`")
    table_html = "<table class='quant-table'><thead><tr><th>PIVOT IDENTIFIED</th><th>TARGET VALUE</th><th>REGIME STATE</th></tr></thead><tbody>"
    for lvl, value in levels.items():
        text_color = "#DC2626" if "R" in lvl else ("#059669" if "S" in lvl else "#2563EB")
        table_html += f"<tr><td style='color: {text_color} !important; font-weight: bold;'>{lvl}</td><td>&#8377; {value:.2f}</td><td>PIVOT LEVEL BASED ON SMARTAPI 15M RANGE</td></tr>"
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)

    try:
        time.sleep(60)
        st.rerun()
    except Exception:
        pass
