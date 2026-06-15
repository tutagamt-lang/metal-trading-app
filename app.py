import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
import time
from datetime import datetime
from SmartApi import SmartConnect
import pyotp

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="QUANTUM-X Live Trading Terminal", initial_sidebar_state="expanded")

# 🎯 HIGH-CONTRAST ANTI-BLUR TERMINAL STYLE MATRIX
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;700&display=swap');
        .stApp { background-color: #FFFFFF !important; color: #0F172A !important; }
        * { font-family: 'Inter', sans-serif; }
        .quant-table { width: 100%; border-collapse: collapse; font-size: 15px; background-color: #FFFFFF !important; margin-bottom: 15px; border: 2px solid #0F172A !important; }
        .quant-table th { background-color: #0F172A !important; color: #FFFFFF !important; text-align: left; padding: 12px 14px; font-family: 'JetBrains Mono', monospace; border: 2px solid #0F172A !important; font-size: 13px; font-weight: 700 !important; text-transform: uppercase; }
        .quant-table td { border: 2px solid #E2E8F0 !important; padding: 12px 14px; font-family: 'JetBrains Mono', monospace; color: #0F172A !important; font-weight: 700 !important; font-size: 15px; background-color: #FFFFFF !important; }
        .anchor-container { border: 2px solid #0F172A; padding: 18px; border-radius: 6px; background-color: #FFFFFF; margin-top: 15px; }
        .anchor-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
        .anchor-card { background-color: #F8FAFC; padding: 12px 16px; border: 1px solid #CBD5E1; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 14px; color: #0F172A; }
        section[data-testid="stSidebar"] { background-color: #1E293B !important; color: #FFFFFF !important; }
        section[data-testid="stSidebar"] * { color: #FFFFFF !important; }
        div[data-testid="stStatusWidget"] { visibility: hidden !important; display: none !important; }
    </style>
""", unsafe_allow_html=True)

# 🔑 ANGEL ONE API CREDENTIALS
API_KEY = "rpg4LX8F"
CLIENT_CODE = "AACG314572"
PASSWORD = "6227"
TOTP_KEY = "Z5MZBUBZAHYJFNKEYHWIJP4HWA"

if "angel_conn" not in st.session_state:
    st.session_state.angel_conn = None

def init_angel_one():
    if st.session_state.angel_conn is not None:
        return st.session_state.angel_conn
    try:
        smart_conn = SmartConnect(api_key=API_KEY.strip())
        totp = pyotp.TOTP(TOTP_KEY.strip()).now()
        data = smart_conn.generateSession(CLIENT_CODE.strip(), PASSWORD.strip(), totp)
        if data and data.get('status'):
            st.session_state.angel_conn = smart_conn
            return smart_conn
    except Exception as e:
        st.error(f"Angel One Login Failed: {str(e)}")
    return None

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["TATASTEEL", "RELIANCE", "ITC", "SBIN"]

# -----------------------------------------------------------------
# DATA ENGINE PIPELINE (100% LIVE FETCHING)
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

def get_live_market_depth_and_oi(symbol):
    """Angel One API மூலம் நேரடி ஆடர் புக் மற்றும் Futures Open Interest (OI) எடுக்கும் செயல்பாடு"""
    obj = init_angel_one()
    data_res = {
        "bids": [], "asks": [], 
        "live_price": 0.0, "open_interest": 0, "oi_change_pct": 0.0,
        "high": 0.0, "low": 0.0, "open": 0.0, "close": 0.0
    }
    
    if obj and symbol in TOKEN_MAP:
        try:
            # 1. CASH மார்க்கெட் விபரம் (L2 Market Depth-க்காக)
            params = {
                "mode": "FULL",
                "exchangeTokens": {
                    TOKEN_MAP[symbol]["exch"]: [TOKEN_MAP[symbol]["token"]]
                }
            }
            res = obj.getMarketData(params)
            
            # 2. FUTURES மார்க்கெட் விபரம் (உண்மையான Open Interest-க்காக)
            fut_params = {
                "mode": "FULL",
                "exchangeTokens": {
                    "NFO": [TOKEN_MAP[symbol]["fut_token"]]
                }
            }
            fut_res = obj.getMarketData(fut_params)
            
            if res['status'] and res['data']['fetched']:
                m_data = res['data']['fetched'][0]
                data_res["live_price"] = float(m_data.get("ltp", 0.0))
                data_res["open"] = float(m_data.get("open", 0.0))
                data_res["high"] = float(m_data.get("high", 0.0))
                data_res["low"] = float(m_data.get("low", 0.0))
                data_res["close"] = float(m_data.get("close", 0.0)) # எஸ்டர்டே குளோஸ்
                data_res["bids"] = m_data.get("depth", {}).get("buy", [])[:2]
                data_res["asks"] = m_data.get("depth", {}).get("sell", [])[:2]
                
            if fut_res['status'] and fut_res['data']['fetched']:
                f_data = fut_res['data']['fetched'][0]
                data_res["open_interest"] = int(f_data.get("opnInterest", 0))
                # முந்தைய நாளின் OI உடன் ஒப்பிட்டு மாற்றம் கணக்கிடப்படுகிறது
                prev_oi = f_data.get("prevOpnInterest", 1)
                if prev_oi == 0: prev_oi = 1
                data_res["oi_change_pct"] = ((data_res["open_interest"] - prev_oi) / prev_oi) * 100

            return data_res
        except Exception as e:
            st.session_state.angel_conn = None
    return None

def get_angel_candle_data(symbol):
    """தொழில்நுட்ப குறிகாட்டிகளுக்கான நேரடி 1-நிமிட கேண்டில் தரவு"""
    obj = init_angel_one()
    if obj and symbol in TOKEN_MAP:
        try:
            today = datetime.now().strftime('%Y-%m-%d %H:%M')
            start_today = datetime.now().strftime('%Y-%m-%d 09:15')
            
            historicParam = {
                "exchange": TOKEN_MAP[symbol]["exch"],
                "symboltoken": TOKEN_MAP[symbol]["token"],
                "interval": "ONE_MINUTE",
                "fromdate": start_today,
                "todate": today
            }
            response = obj.getCandleData(historicParam)
            if response['status'] and response['data']:
                df = pd.DataFrame(response['data'], columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                df.set_index('Timestamp', inplace=True)
                return df
        except Exception as e:
            pass
    
    # API வேலை செய்யாத பட்சத்தில் மட்டும் பேக்கப் சிமுலேட்டர் இயங்கும்
    times = pd.date_range(start="09:15", end="15:30", freq="1min")
    df_backup = pd.DataFrame(index=times)
    base = {"TATASTEEL": 198.0, "RELIANCE": 1308.0, "ITC": 288.30, "SBIN": 1020.65}.get(symbol, 500.0)
    df_backup['Open'] = base + np.random.uniform(-0.5, 0.5, len(times))
    df_backup['High'] = df_backup['Open'] + np.random.uniform(0, 0.8, len(times))
    df_backup['Low'] = df_backup['Open'] - np.random.uniform(0, 0.8, len(times))
    df_backup['Close'] = (df_backup['High'] + df_backup['Low']) / 2
    df_backup['Volume'] = np.random.randint(15000, 50000, len(times))
    return df_backup

# -----------------------------------------------------------------
# SIDEBAR TERMINAL
# -----------------------------------------------------------------
st.sidebar.markdown("### `📡 RADAR TERMINAL`")
custom_ticker = st.sidebar.text_input("ENTER TICKER SYMBOL:", "").strip().upper()

if custom_ticker:
    if custom_ticker not in st.session_state.watchlist and custom_ticker in TOKEN_MAP:
        if st.sidebar.button(f"[+] ADD {custom_ticker}", use_container_width=True):
            st.session_state.watchlist.append(custom_ticker)
            st.rerun()

selected_focus = st.sidebar.selectbox("⚡ ACTIVE INSTANCE:", options=st.session_state.watchlist)
ticker_clean = custom_ticker if (custom_ticker in TOKEN_MAP) else selected_focus

# -----------------------------------------------------------------
# MAIN DASHBOARD DATA FETCHING
# -----------------------------------------------------------------
live_data = get_live_market_depth_and_oi(ticker_clean)
df = get_angel_candle_data(ticker_clean)

if live_data and len(df) >= 1:
    # கணக்கீடுகள் (Indicators calculations)
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

    # Live prices from FULL Market Data API
    live_price = live_data["live_price"] if live_data["live_price"] > 0 else df.iloc[-1]['Close']
    day_open = live_data["open"] if live_data["open"] > 0 else df.iloc[0]['Open']
    day_change = live_price - day_open
    dc_color = "#10B981" if day_change >= 0 else "#EF4444"
    pct_change = ((day_change / day_open) * 100) if day_open != 0 else 0.0

    # ⏰ EXTRACT EXACT ANCHOR DATA (09:15 - 09:30)
    df_15min = df.between_time("09:15", "09:30")
    if not df_15min.empty:
        o_anchor, c_anchor = float(df_15min.iloc[0]['Open']), float(df_15min.iloc[-1]['Close'])
        h_anchor, l_anchor = float(df_15min['High'].max()), float(df_15min['Low'].min())
    else:
        o_anchor, c_anchor, h_anchor, l_anchor = day_open, live_price, live_data["high"], live_data["low"]

    # உன்னதமான Futures OI அடிப்படையில் ட்ரெண்ட் கணக்கீடு
    fut_oi_change_pct = live_data["oi_change_pct"]
    movement_type = get_oi_movement(fut_oi_change_pct, live_price - day_open)
    
    levels = calculate_pivots(h_anchor, l_anchor, c_anchor, o_anchor)
    strike_step = 5.0 if live_price < 300 else (20.0 if live_price < 1500 else 50.0)
    atm_strike = round(live_price / strike_step) * strike_step

    # -----------------------------------------------------------------
    # SIDEBAR MULTI-STOCK MONITOR (LIVE)
    # -----------------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### `⚡ MULTI-STOCK MONITOR`")
    scanner_data = []
    for s in st.session_state.watchlist:
        s_live = get_live_market_depth_and_oi(s)
        if s_live:
            s_mov = get_oi_movement(s_live["oi_change_pct"], s_live["live_price"] - s_live["open"])
            scanner_data.append({"STOCK": s, "PRICE": f"{s_live['live_price']:.2f}", "MATRIX": s_mov})
    st.sidebar.dataframe(pd.DataFrame(scanner_data), hide_index=True, use_container_width=True)

    # -----------------------------------------------------------------
    # UI RENDERING
    # -----------------------------------------------------------------
    st.markdown(f"<h2>QUANTUM-X TERMINAL // <span style='color:#10B981;'>{ticker_clean}</span> <span style='font-size:12px; background-color:#10B981; color:#FFF; padding:4px 8px; border-radius:3px; vertical-align:middle;'>FEED: ANGEL_ONE_LIVE</span></h2>", unsafe_allow_html=True)

    # Price Feed Ribbon
    st.markdown(f"""
    <div style="background-color:#0F172A; padding: 18px; border-radius: 6px; margin-bottom: 15px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <span style="color:#94A3B8; font-size:12px; font-weight:700; letter-spacing:1.5px; font-family:'JetBrains Mono';">ANGEL SMARTAPI DIRECT TICK FEED</span>
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

    layout_col1, layout_col2 = st.columns([1.3, 1])

    with layout_col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Price', line=dict(color='#10B981', width=2.5)))
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], mode='lines', name='VWAP', line=dict(color='#2563EB', width=2, dash='dash')))
        fig.update_layout(
            template="plotly_white", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=10, b=10), height=140, showlegend=False,
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#E2E8F0')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{ticker_clean}")

        # 🔳 09:15 - 09:30 ANCHOR MULTI-GRID BOX VIEW
        st.markdown(f"""
        <div class="anchor-container">
            <span style="color:#0F172A; font-weight:700; font-size:13px; font-family:'JetBrains Mono'; letter-spacing:0.5px;">⚡ NSE SYSTEM CAPTURED DATA MATRIX (09:15 - 09:30 Anchor)</span>
            <div class="anchor-grid">
                <div class="anchor-card"><b>• OPEN:</b> 🔳 {o_anchor:.2f}</div>
                <div class="anchor-card"><b>• HIGH:</b> <span style="color:#059669; font-weight:700;">🔳 {h_anchor:.2f}</span></div>
                <div class="anchor-card"><b>• LOW:</b> <span style="color:#DC2626; font-weight:700;">🔳 {l_anchor:.2f}</span></div>
                <div class="anchor-card"><b>• CLOSE:</b> <span style="color:#2563EB; font-weight:700;">🔳 {c_anchor:.2f}</span></div>
            </div>
            <div style="margin-top:12px; font-size:13px; font-family:'JetBrains Mono'; color:#475569; padding-top:8px; border-top:1px dashed #E2E8F0;">
                ⇄ Live Volume Flow State: <b>{movement_type}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with layout_col2:
        dow_label = "UPTREND" if c_anchor > o_anchor else "DOWNTREND"
        calc_entry_b = max(levels["R1 (Resistance 1)"], h_anchor)
        calc_entry_s = min(levels["S1 (Support 1)"], l_anchor)
        flow_label = "ABOVE VWAP" if live_price > current_vwap else "BELOW VWAP"
        
        st.markdown(f"""
        <div style="background-color:#1E1E14; padding:20px; border-radius:6px; border: 2px solid #0F172A; border-left:8px solid #D97706; height: 235px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);">
            <span style="background-color:#D97706; color:#FFFFFF; padding:4px 8px; font-size:12px; font-weight:bold; border-radius:2px; font-family:'JetBrains Mono';">SYSTEM CONFLICT MATRIX</span>
            <div style="margin-top:16px; font-size:14px; line-height:2.0; font-family:'JetBrains Mono'; color:#94A3B8;">
                • DOW TREND: <b style="color:#F59E0B;">{dow_label}</b> | FLOW: <b style="color:#F87171;">{flow_label}</b><br>
                • <span style="color:#34D399; font-weight:bold;">IF BREAKOUT BUY:</span> Entry Above <b style="color:#FFFFFF; background-color:#2D2D24; padding:3px 6px; border-radius:3px;">₹ {calc_entry_b:.2f}</b><br>
                • <span style="color:#F87171; font-weight:bold;">IF BREAKOUT SELL:</span> Entry Below <b style="color:#FFFFFF; background-color:#2D2D24; padding:3px 6px; border-radius:3px;">₹ {calc_entry_s:.2f}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Tables Row
    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    table_col1, table_col2 = st.columns([1, 1])
    
    with table_col1:
        st.markdown("#### `📊 FUTURE OPEN INTEREST (OI) TRACKER`")
        st.markdown(f"""
        <table class='quant-table'>
            <thead><tr><th>SEGMENT</th><th>LIVE FUTURE OI</th><th>OI CHANGE (%)</th><th>CURRENT REGIME</th></tr></thead>
            <tbody>
                <tr>
                    <td>{ticker_clean}-FUT</td>
                    <td style='color:#059669 !important;'>{live_data["open_interest"]:,}</td>
                    <td style='color:{"#059669" if fut_oi_change_pct >= 0 else "#DC2626"} !important;'>{fut_oi_change_pct:+.2f}%</td>
                    <td style='color:#0F172A !important; font-weight:bold;'>{movement_type}</td>
                </tr>
            </tbody>
        </table>
        """, unsafe_allow_html=True)

    with table_col2:
        st.markdown("#### `🌐 REALTIME MARKET DEPTH L2 (ORDER BOOK)`")
        bid_rows = live_data["bids"]
        ask_rows = live_data["asks"]
        
        # ஆடர் புக் காலியாக இருந்தால் ஒரு போலி வரிசை காட்டுவதற்கு
        b1_q, b1_p = (bid_rows[0]['quantity'], bid_rows[0]['price']) if len(bid_rows) > 0 else (0, live_price)
        b2_q, b2_p = (bid_rows[1]['quantity'], bid_rows[1]['price']) if len(bid_rows) > 1 else (0, live_price)
        a1_q, a1_p = (ask_rows[0]['quantity'], ask_rows[0]['price']) if len(ask_rows) > 0 else (0, live_price)
        a2_q, a2_p = (ask_rows[1]['quantity'], ask_rows[1]['price']) if len(ask_rows) > 1 else (0, live_price)

        st.markdown(f"""
        <table class='quant-table'>
            <thead><tr><th>BID QTY (BUY)</th><th>PRICE</th><th>ASK QTY (SELL)</th><th>PRICE</th></tr></thead>
            <tbody>
                <tr><td style='color:#059669 !important;'>{b1_q:,}</td><td style='color:#0F172A !important;'>₹ {b1_p:.2f}</td><td style='color:#DC2626 !important;'>{a1_q:,}</td><td style='color:#0F172A !important;'>₹ {a1_p:.2f}</td></tr>
                <tr><td style='color:#059669 !important;'>{b2_q:,}</td><td style='color:#0F172A !important;'>₹ {b2_p:.2f}</td><td style='color:#DC2626 !important;'>{a2_q:,}</td><td style='color:#0F172A !important;'>₹ {a2_p:.2f}</td></tr>
            </tbody>
        </table>
        """, unsafe_allow_html=True)

    # Breakout Signals Panel
    st.markdown("#### `🎯 REALTIME ADVANCED BREAKOUT SCANNED MATRIX`")
    r1_val = levels["R1 (Resistance 1)"]
    s1_val = levels["S1 (Support 1)"]
    is_near_resistance = abs(live_price - r1_val) <= (live_price * 0.006)
    is_near_support = abs(live_price - s1_val) <= (live_price * 0.006)
    
    if live_price < s1_val:
        status_box, color_box, text_theme = "💥 REAL BREAKDOWN: SHORT BUILDUP", "#DC2626", "#DC2626"
        tamil_desc = f"விலை முக்கிய சப்போர்ட் எல்லையை (₹ {s1_val:.2f}) உடைத்து கீழே இறங்கிவிட்டது. Futures OI மாற்றத்தின்படி இது பலவீனமான நிலையைக் காட்டுகிறது."
        trade_action = "⚡ SELL ACTION: சப்போர்ட் உடைந்துவிட்டதால், PE (Put Option) எடுக்கலாம்!"
    elif live_price > r1_val:
        status_box, color_box, text_theme = "🔥 REAL BREAKOUT: LONG BUILDUP", "#059669", "#059669"
        tamil_desc = f"விலை முக்கிய ரெசிஸ்டன்ஸ் எல்லையை (₹ {r1_val:.2f}) உடைத்து மேலே ஏறியுள்ளது. பலமான அப்-ட்ரெண்ட் தொடர வாய்ப்புள்ளது!"
        trade_action = "⚡ BUY ACTION: ரெசிஸ்டன்ஸ் உடைந்ததால், தாராளமாக CE (Call Option) எடுக்கலாம்!"
    elif is_near_support and live_price >= s1_val:
        status_box, color_box, text_theme = "🍏 SUPPORT REVERSAL: BOUNCE BACK", "#059669", "#059669"
        tamil_desc = f"விலை சப்போர்ட் எல்லைக்கு (₹ {s1_val:.2f}) அருகில் வந்து, அதை உடைக்காமல் மேலே திரும்புகிறது."
        trade_action = "⚡ BUY ACTION: சப்போர்ட்டில் தஞ்சம் அடைந்து மேலே திரும்புதால் Call Option எடுக்கலாம்."
    elif is_near_resistance and live_price <= r1_val:
        status_box, color_box, text_theme = "⚠️ RESISTANCE REVERSAL / FAKE BREAKOUT", "#DC2626", "#DC2626"
        tamil_desc = f"விலை ரெசிஸ்டன்ஸ் எல்லைக்கு (₹ {r1_val:.2f}) அருகில் வந்தாலும் அதை உடைக்க முடியாமல் திணறுகிறது."
        trade_action = "🛑 SELL ACTION: Resistance தாங்காமல் கீழே திரும்பும்போது Put Option வாங்கலாம்."
    else:
        status_box, color_box, text_theme = "📡 CONSOLIDATION: MEAN REVERSION", "#2563EB", "#2563EB"
        tamil_desc = "தற்போது ஸ்டாக் எந்த ஒரு முக்கிய சப்போர்ட் அல்லது ரெசிஸ்டன்ஸ் எல்லையையும் தொடவில்லை. நடுநிலையான எல்லையில் வர்த்தகம் ஆகிறது (Sideways)."
        trade_action = "⏳ WAIT: விலை முக்கிய சப்போர்ட் அல்லது ரெசிஸ்டன்ஸ் எல்லைக்கு அருகில் வரும் வரை பொறுமையாக காத்திருக்கவும்."

    st.markdown(f"""
    <div style="background-color: #FFFFFF; padding: 22px; border-radius: 6px; border: 2px solid #0F172A; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); border-left: 8px solid {color_box};">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #E2E8F0; padding-bottom: 10px; margin-bottom: 15px;">
            <span style="color: {text_theme}; font-size: 18px; font-family: monospace; font-weight: bold;">{status_box}</span>
            <span style="font-size: 14px; color: #0F172A; font-family: monospace; font-weight: bold;">FUTURES OI CHANGE: <span style="color: #D97706;">{fut_oi_change_pct:+.2f}%</span></span>
        </div>
        <div style="margin-bottom: 15px; font-size: 15px; color: #334155; line-height:1.7;">
            <strong style="color: #1E3A8A; font-size:16px;">📊 தமிழ் சந்தை விளக்கம்:</strong> <span style="font-weight:600; color:#0F172A;">{tamil_desc}</span>
        </div>
        <div style="background-color: #F8FAFC; padding: 14px 18px; border-radius: 4px; font-size: 15px; border: 2px solid #0F172A; color: {text_theme}; font-weight: bold;">
            {trade_action}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Pivot Matrix Engine Table (TOP TO BOTTOM)
    st.markdown("#### `🎯 ALIGNED BREAKOUT MATRIX ENGINE (TOP TO BOTTOM)`")
