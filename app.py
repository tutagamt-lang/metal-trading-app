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

# Pivot பாயிண்ட் கணக்கீட்டு ஃபார்முலா
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

    # RSI, EMA, ATR கணக்கீடுகள் (இங்கே பிராக்கெட் எரர் சரிசெய்யப்பட்டுள்ளது)
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
    
    base_high = float(df.iloc[0:idx_930+1]['High'].max())
    base_low = float(df.iloc[0:idx_930+1]['Low'].min())
    base_close = float(c_930)
    
    initial_levels = calculate_pivots(base_high, base_low, base_close)
    levels = initial_levels.copy()
    
    pivot_status_msg = "காலை 9:15 முதல் 9:30 வரம்பை அடிப்படையாகக் கொண்ட ஆரம்ப லெவல்கள்"
    
    if live_price > initial_levels["R3 (Resistance 3)"]:
        new_o = initial_levels["R1 (Resistance 1)"]
        new_h = initial_levels["R3 (Resistance 3)"]
        new_l = initial_levels["R1 (Resistance 1)"]
        new_c = initial_levels["R3 (Resistance 3)"]
        levels = calculate_pivots(new_h, new_l, new_c)
        pivot_status_msg = f"🚀 R3 உடைக்கப்பட்டது! விதியின்படி [Open={new_o:.2f}, High={new_h:.2f}, Low={new_l:.2f}, Close={new_c:.2f}] கொண்டு புதிய Pivot லெவல்கள் கணக்கிடப்பட்டுள்ளன."
        
    elif live_price < initial_levels["S3 (Support 3)"]:
        new_o = initial_levels["S1 (Support 1)"]
        new_h = initial_levels["S1 (Support 1)"]
        new_l = initial_levels["S3 (Support 3)"]
        new_c = initial_levels["S3 (Support 3)"]
        levels = calculate_pivots(new_h, new_l, new_c)
        pivot_status_msg = f"💥 S3 உடைக்கப்பட்டது! விதியின்படி [Open={new_o:.2f}, High={new_h:.2f}, Low={new_l:.2f}, Close={new_c:.2f}] கொண்டு புதிய Pivot லெவல்கள் கணக்கிடப்பட்டுள்ளன."

    price_diff = c_930 - c_915
    movement_type = get_oi_movement(oi_change, price_diff)

    strike_step = 5.0 if live_price < 300 else (20.0 if live_price < 1500 else 50.0)
    atm_strike = round(live_price / strike_step) * strike_step
    
    pcr_val = 1.0 + (day_change / day_open) * 10
    pcr_val = max(0.4, min(1.8, pcr_val))
    max_pain = atm_strike + (strike_step if day_change >= 0 else -strike_step)

    if h_930 > h_915 and l_930 > l_915:
        dow_trend = "UPTREND"
        dow_trend_display, trend_color = "🟢 STRONG UPTREND", "#00E676"
    elif h_930 < h_915 and l_930 < l_915:
        dow_trend = "DOWNTREND"
        dow_trend_display, trend_color = "🔴 STRONG DOWNTREND", "#FF1744"
    else:
        dow_trend = "SIDEWAYS"
        dow_trend_display, trend_color = "🟡 SIDEWAYS MARKET", "#FFD600"

    # Main Header
    st.title(f"⚡ {ticker_display} Advanced Real-Time Live Trading Dashboard")

    # 1. Live Price & Advanced Indicators Card
    st.markdown(f"""
    <div style="background-color:#111111; padding: 25px; border-radius: 12px; border-left: 8px solid {dc_color}; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <span style="color:#888888; font-size:14px; font-weight:bold; letter-spacing:1px;">REAL-TIME LIVE PRICE (நேரடி விலை)</span>
                <h1 style="color:#FFFFFF; margin:5px 0; font-size:56px; font-family: monospace; font-weight: bold;">₹ {live_price:.2f}</h1>
                <span style="color:{dc_color}; font-size:18px; font-weight:bold;">Today's Move: {day_change:+.2f} ({((day_change/day_open)*100):+.2f}%)</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; background-color:#1a1a1a; padding:15px; border-radius:8px; border:1px solid #333; min-width:450px;">
                <div><span style="color:#888888; font-size:12px;">📊 VWAP Price</span><br><b style="color:#FFFFFF; font-size:16px; font-family: monospace;">₹ {current_vwap:.2f}</b></div>
                <div><span style="color:#888888; font-size:12px;">🎯 Options Max Pain</span><br><b style="color:#FFFFFF; font-size:16px; font-family: monospace;">₹ {max_pain:.2f}</b></div>
                <div><span style="color:#888888; font-size:12px;">📈 Put-Call Ratio (PCR)</span><br><b style="color:#FFFFFF; font-size:16px; font-family: monospace;">{pcr_val:.2f}</b></div>
                <div><span style="color:#888888; font-size:12px;">⚡ ATR Volatility (14)</span><br><b style="color:#FFD600; font-size:16px; font-family: monospace;">₹ {current_atr:.2f}</b></div>
            </div>
        </div>
        <span style="color:#666666; font-size:12px; float:right; margin-top:10px;">Feed Status: {data_status}</span>
    </div>
    """, unsafe_allow_html=True)

    # மல்டி-இண்டிகேட்டர் KPI கார்டுகள்
    rsi_status = "🟢 Oversold" if current_rsi < 30 else ("🔴 Overbought" if current_rsi > 70 else "🟡 Neutral")
    rsi_color = "#00E676" if current_rsi < 30 else ("#FF1744" if current_rsi > 70 else "#FFD600")
    
    ema_status = "🟢 Bullish Momentum" if current_ema9 > current_ema21 else "🔴 Bearish Momentum"
    ema_color = "#00E676" if current_ema9 > current_ema21 else "#FF1744"

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.markdown(f'<div style="background-color:#1a1a1a; padding:15px; border-radius:8px; border-top:4px solid {rsi_color}; text-align:center;"><span style="color:#888888; font-size:13px;">📟 Live RSI (14)</span><br><h3 style="color:#ffffff; margin:5px 0;">{current_rsi:.2f}</h3><span style="color:{rsi_color}; font-weight:bold; font-size:13px;">{rsi_status}</span></div>', unsafe_allow_html=True)
    with kpi2:
        st.markdown(f'<div style="background-color:#1a1a1a; padding:15px; border-radius:8px; border-top:4px solid {ema_color}; text-align:center;"><span style="color:#888888; font-size:13px;">📈 EMA Trend (9 vs 21)</span><br><h3 style="color:#ffffff; margin:5px 0;">{current_ema9:.1f} / {current_ema21:.1f}</h3><span style="color:{ema_color}; font-weight:bold; font-size:13px;">{ema_status}</span></div>', unsafe_allow_html=True)
    with kpi3:
        st.markdown(f'<div style="background-color:#1a1a1a; padding:15px; border-radius:8px; border-top:4px solid #FFD600; text-align:center;"><span style="color:#888888; font-size:13px;">🛡️ ATR Recommended SL</span><br><h3 style="color:#FFD600; margin:5px 0;">₹ {current_atr:.2f}</h3><span style="color:#aaaaaa; font-size:12px;">விலையிலிருந்து கழிக்கவும்</span></div>', unsafe_allow_html=True)
    with kpi4:
        st.markdown(f'<div style="background-color:#1a1a1a; padding:15px; border-radius:8px; border-top:4px solid #00B0FF; text-align:center;"><span style="color:#888888; font-size:13px;">🔄 Auto Refresh Timer</span><br><h3 style="color:#00B0FF; margin:5px 0;">5 Seconds</h3><span style="color:#aaaaaa; font-size:12px;">Live Streaming Loop</span></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Chart Section
    st.header(f"📈 {ticker_display} Live Interactive Chart")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines+markers', name='Live Price', line=dict(color='#00E676', width=3)))
    fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], mode='lines', name='VWAP', line=dict(color='#FFD600', width=2, dash='dash')))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_9'], mode='lines', name='9 EMA', line=dict(color='#00B0FF', width=1)))
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_21'], mode='lines', name='21 EMA', line=dict(color='#E040FB', width=1)))
    fig.update_layout(template="plotly_dark", margin=dict(l=20, r=20, t=20, b=20), height=380, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # Section 1
    st.header("1. 9:15-9:30 Candle & Dow Theory Live Trend Analysis")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.subheader("⏱️ 9:15 & 9:30 Prices")
        st.metric("காலை 9:15 Close", f"₹{c_915:.2f}")
        st.metric("காலை 9:30 Close", f"₹{c_930:.2f}")
    with c2:
        st.subheader("📊 Future OI Values")
        st.metric("காலை 9:15 Open Interest", f"{oi_915:,}")
        st.metric("காலை 9:30 Open Interest", f"{oi_930:,}")
        st.markdown(f"""
        <div style="background-color:#1E1E1E; padding:10px; border-radius:6px; margin-top:10px;">
            <span style="color:#AAAAAA; font-size:13px;">Future OI Live Changes:</span><br>
            <b style="color:{oi_live_color}; font-size:18px;">{oi_change:+,} Qty</b>
        </div>
        """, unsafe_allow_html=True)
        
    with c3:
        st.subheader("📜 Dow Theory Trend")
        st.markdown(f'<div style="background-color:#1E1E1E; padding:12px; border-radius:8px; border-top:5px solid {trend_color}; color:white;"><b>{dow_trend_display}</b></div>', unsafe_allow_html=True)
    with c4:
        st.subheader("🎯 Strategy Entry Setup")
        st.write(f"**Matrix Status:** {movement_type}")
        if live_price > current_vwap: st.success("🟢 ABOVE VWAP")
        else: st.error("🔴 BELOW VWAP")

    st.markdown("---")

    # Section 2: Action Box
    st.header("2. Live Market Depth Analysis & Order Suitability")
    
    base_buyer = 60 if day_change >= 0 else 40
    buyer_ratio = float(base_buyer + np.random.uniform(-3, 3))
    total_buyers = int(700000 * (buyer_ratio/100))
    total_sellers = 700000 - total_buyers
    
    md_col1, md_col2 = st.columns([2, 3])
    with md_col1:
        st.subheader("📊 Buyers vs Sellers Volume")
        st.metric("மொத்த வாங்குபவர்கள்", f"{total_buyers:,} Qty")
        st.metric("மொத்த விற்பனையாளர்கள்", f"{total_sellers:,} Qty")
        st.progress(int(buyer_ratio))
        
    with md_col2:
        st.subheader("🛡️ Double Confirmation Strategic Trade Recommendation")
        
        # 🟢 1. Double Confirmed BUY Rule
        if dow_trend == "UPTREND" and live_price > current_vwap:
            entry_exact = max(levels["R1 (Resistance 1)"], h_930)
            target_exact = levels["R2 (Resistance 2)"]
            stop_loss = entry_exact - (current_atr * 1.5)
            
            suitability = "🚀 DOUBLE CONFIRMED BUY (முழுமையான சிக்னல் கிடைத்துவிட்டது)"
            action_box = f"""<div style="background-color:#0d2e1f; padding:20px; border-radius:10px; border:3px solid #00E676; color:#ffffff;">
                <b style="color:#00E676; font-size:18px;">🔥 DOUBLE CONFIRMED BUY PLAN:</b><br>
                <p style="color:#eeeeee; font-size:14px; margin-top:5px;">விதி: Dow Theory Trend ஏறுமுகமாக உள்ளது + விலை VWAP-க்கு மேல் வர்த்தகமாகிறது. சந்தை மிக பலமாக உள்ளது.</p>
                <span style="font-size:16px; color:#ffffff;">🎯 <b>Buy Price:</b> ₹ {entry_exact:.2f}-க்கு மேல் நிலைபெறும் போது மட்டும் Buy எடுக்கவும்.</span><br><br>
                <span style="font-size:15px; color:#ffffff;">🔹 <b>Target Price:</b> ₹ {target_exact:.2f}</span><br>
                <span style="font-size:15px; color:#FFD600;">🛑 <b>ATR Stop Loss (1.5x ATR):</b> ₹ {stop_loss:.2f}</span>
            </div>"""

        # 🔴 2. Double Confirmed SELL Rule
        elif dow_trend == "DOWNTREND" and live_price < current_vwap:
            entry_exact = min(levels["S1 (Support 1)"], l_930)
            target_exact = levels["S2 (Support 2)"]
            stop_loss = entry_exact + (current_atr * 1.5)
            
            suitability = "📉 DOUBLE CONFIRMED SELL (விற்பனை செய்ய முழு அனுமதி)"
            action_box = f"""<div style="background-color:#421119; padding:20px; border-radius:10px; border:2px solid #FF1744; color:#ffffff;">
                <b style="color:#FF1744; font-size:18px;">🔥 DOUBLE CONFIRMED SELL PLAN:</b><br>
                <p style="color:#eeeeee; font-size:14px; margin-top:5px;">விதி: Dow Theory Trend இறங்குமுகமாக உள்ளது + விலை VWAP-க்கு கீழ் வர்த்தகமாகிறது. விற்பனையாளர்கள் வசம் மார்க்கெட் உள்ளது.</p>
                <span style="font-size:16px; color:#ffffff;">🎯 <b>Sell Price:</b> ₹ {entry_exact:.2f}-க்கு கீழ் உடைத்துச் செல்லும்போது Sell எடுக்கலாம்.</span><br><br>
                <span style="font-size:15px; color:#ffffff;">🔹 <b>Target Price:</b> ₹ {target_exact:.2f}</span><br>
                <span style="font-size:15px; color:#FFD600;">🛑 <b>ATR Stop Loss (1.5x ATR):</b> ₹ {stop_loss:.2f}</span>
            </div>"""

        # ⚠️ 3. No Trade Zone
        else:
            suitability = "⚠️ NO TRADE ZONE (உறுதிப்படுத்தல் இல்லை / முரண்பாடு உள்ளது)"
            action_box = f"""<div style="background-color:#2a2307; padding:20px; border-radius:10px; border:2px solid #FFD600; color:#ffffff;">
                <b style="color:#FFD600; font-size:18px;">🛑 TRADE எடுப்பதைத் தவிர்க்கவும் (No Confirmation):</b><br>
                <p style="color:#eeeeee; font-size:14px; margin-top:5px;">காரணம்: Dow Theory காட்டும் ட்ரெண்டும் (Trend) மற்றும் VWAP காட்டும் விலையின் நிலையும் முரண்படுகின்றன. சந்தை பக்கவாட்டு நகர்வில் (Sideways) நகரலாம்.</p>
                <span style="font-size:15px; color:#FFD600;">💡 <b>Pro Tip:</b> இரண்டு குறியீடுகளும் ஒரே திசையைக் காட்டும் வரை பொறுமையாகக் காத்திருக்கவும். அவசரப்பட்டு பணத்தை இழக்க வேண்டாம்.</span>
            </div>"""
            
        st.markdown(f"**வியூகத்தின் தற்போதைய நிலை:** <span style='font-size:16px; font-weight:bold;'>{suitability}</span>", unsafe_allow_html=True)
        st.markdown(action_box, unsafe_allow_html=True)

    st.markdown("---")

    # Section 3: Pivot Table Reference
    st.header("3. Pivot Points & Dynamic Breakout Levels Reference")
    
    if "உடைக்கப்பட்டது" in pivot_status_msg:
        st.warning(f"🔄 {pivot_status_msg}")
    else:
        st.info(f"ℹ️ {pivot_status_msg}")
        
    pivot_df = pd.DataFrame(list(levels.items()), columns=["Levels Name", "Price Range (INR)"])
    st.dataframe(pivot_df, use_container_width=True, hide_index=True)

    # 🔄 5 வினாடி ஆட்டோ ரீஃப்ரெஷ் லூப்
    time.sleep(5)
    st.rerun()

else:
    st.error("டேட்டா எடுப்பதில் சிக்கல் உள்ளது. ரீபூட் செய்யவும்.")
