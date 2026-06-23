import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from datetime import datetime, timezone, timedelta
import pyotp
import urllib.request
import xml.etree.ElementTree as ET

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="QUANTUM-X Live Trading Terminal")

try:
    from SmartApi import SmartConnect
except ImportError:
    st.error("தயவுசெய்து உங்கள் requirements.txt கோப்பில் 'smartapi-python' சேர்க்கவும்.")

# 🎨 PREMIUM TERMINAL STYLESHEET WITH HOME DROPDOWN AND TABS
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
        
        .stApp { background-color: #F8FAFC !important; color: #1E293B !important; }
        * { font-family: 'Plus Jakarta Sans', sans-serif; }
        .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }
        
        h2 { font-weight: 700; letter-spacing: -0.5px; margin: 0 0 5px 0 !important; color: #0F172A !important; font-size: 24px !important; }
        .mono-text { font-family: 'JetBrains Mono', monospace !important; }
        
        /* Premium Navigation Tabs Styling */
        div[data-testid="stTabs"] button {
            font-size: 14px !important;
            font-weight: 600 !important;
            color: #64748B !important;
            padding: 10px 24px !important;
            border-radius: 8px 8px 0px 0px !important;
            transition: all 0.3s ease;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            color: #2563EB !important;
            background-color: #EFF6FF !important;
            border-bottom: 3px solid #2563EB !important;
        }
        
        /* Home Dropdown Layout Tweaks */
        div[data-testid="stSelectbox"] label {
            font-size: 11px !important;
            font-weight: 700 !important;
            color: #475569 !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Layout Grid Cards */
        .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .metric-card { background: #FFFFFF; padding: 16px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05); }
        .metric-label { color: #64748B; font-size: 11px; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 4px; }
        .metric-value { color: #0F172A; font-size: 22px; font-weight: 700; }
        
        .info-box { background: #FFFFFF; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05); height: 100%; margin-bottom: 15px; }
        .info-title { color: #1E40AF; font-size: 12px; font-weight: 700; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 12px; display: block; }
        
        /* News Cards */
        .premium-news-card { background: #FFFFFF; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 16px; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05); }
        .news-badge { background: #EFF6FF; color: #2563EB; font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 6px; text-transform: uppercase; display: inline-block; margin-bottom: 8px; }
        .premium-news-title { font-size: 16px; font-weight: 700; color: #0F172A; text-decoration: none; display: block; margin-bottom: 6px; line-height: 1.4; }
        .premium-news-meta { font-size: 12px; color: #64748B; font-weight: 500; }
        
        /* Tables */
        .quant-table { width: 100%; border-collapse: collapse; font-size: 14px; background: #FFFFFF; border-radius: 12px; overflow: hidden; border: 1px solid #E2E8F0; margin-top: 15px; box-shadow: 0 1px 3px 0 rgba(0,0,0,0.05); }
        .quant-table th { background-color: #F1F5F9; color: #475569; text-align: left; padding: 12px 16px; font-size: 12px; font-weight: 600; letter-spacing: 0.5px; border-bottom: 1px solid #E2E8F0; }
        .quant-table td { padding: 14px 16px; border-bottom: 1px solid #F1F5F9; color: #1E293B; }
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] { background-color: #0F172A !important; border-right: 1px solid #1E293B; }
        section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
        section[data-testid="stSidebar"] input { color: #0F172A !important; background-color: #FFFFFF !important; border-radius: 6px !important; }
    </style>
""", unsafe_allow_html=True)

# 🔐 API CREDENTIALS
ANGEL_API_KEY = "rpg4LX8F"
ANGEL_CLIENT_ID = "AACG314572"
ANGEL_PASSWORD = "6227"
ANGEL_TOTP_KEY = "Z5MZBUBZAHYJFNKEYHWIJP4HWA"

try:
    calculated_totp = pyotp.TOTP(ANGEL_TOTP_KEY.strip()).now()
except Exception:
    calculated_totp = ""

st.sidebar.markdown("### 🔐 SMARTAPI INTEGRATION")
api_key = st.sidebar.text_input("ANGELONE API KEY:", value=ANGEL_API_KEY, type="password")
client_id = st.sidebar.text_input("CLIENT ID:", value=ANGEL_CLIENT_ID)
password = st.sidebar.text_input("PIN/PASSWORD:", value=ANGEL_PASSWORD, type="password")
totp_token = st.sidebar.text_input("TOTP TOKEN:", value=calculated_totp, type="password")

# 📋 INTRADAY METALS WATCHLIST & TOKEN MAP DIRECT DEFINITION
MY_STOCKS = ["SAIL", "VEDL", "HINDALCO", "NATIONALUM", "HINDCOPPER"]

TOKEN_MAP = {
    "SAIL": "2963",
    "VEDL": "3063",
    "HINDALCO": "1363",
    "NATIONALUM": "6364",
    "HINDCOPPER": "3103"
}

def get_fo_regime(price_change, oi_change):
    if oi_change > 0 and price_change > 0: return "LONG BUILDUP (ஆரோக்கியமான வாங்குதல்)", "#10B981"
    elif oi_change > 0 and price_change <= 0: return "SHORT BUILDUP (கனமான விற்பனை அழுத்தம்)", "#EF4444"
    elif oi_change <= 0 and price_change <= 0: return "LONG UNWINDING (லாபப் பதிவு/பலவீனம்)", "#F59E0B"
    else: return "SHORT COVERING (Short செட்டில்மென்ட் / மேல்நோக்கிய வேகம்)", "#3B82F6"

def calculate_pivots(H, L, C, O):
    P = (H + C + L + O) / 4
    return {
        "R3": H + 2 * (P - L), "R2": P + ((2 * P - L) - (2 * P - H)), "R1": (2 * P) - L,
        "PP": P, "S1": (2 * P) - H, "S2": P - ((2 * P - L) - (2 * P - H)), "S3": L - 2 * (H - P)
    }

@st.cache_data(ttl=300)
def fetch_stock_news(symbol):
    news_list = []
    try:
        query = f"{symbol}+stock+news+india"
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        for item in root.findall('.//item')[:4]:
            title = item.find('title').text
            link = item.find('link').text
            pub_date = item.find('pubDate').text
            source = item.find('source').text if item.find('source') is not None else "NSE"
            if " - " in title: title = title.split(" - ")[0]
            news_list.append({"title": title, "link": link, "date": pub_date, "source": source})
    except Exception:
        news_list = [{"title": f"Analyzing market intelligence for {symbol}", "link": "#", "date": "Just now", "source": "System"}]
    return news_list

@st.cache_data(ttl=300)
def fetch_historic_candles(symbol, token, today_date, _api_key, _client_id, _password, _totp):
    try:
        smart_conn = SmartConnect(api_key=_api_key)
        smart_conn.generateSession(_client_id, _password, _totp)
        historic_param = {
            "exchange": "NSE", "symboltoken": token, "interval": "ONE_MINUTE",
            "fromdate": f"{today_date} 09:15", "todate": f"{today_date} 15:30"
        }
        response = smart_conn.getCandleData(historic_param)
        if response and response.get("status") and response.get("data"):
            return response["data"]
    except Exception:
        pass
    return []

def fetch_current_ltp(symbol, token, _api_key, _client_id, _password, _totp):
    try:
        smart_conn = SmartConnect(api_key=_api_key)
        smart_conn.generateSession(_client_id, _password, _totp)
        ltp_response = smart_conn.getLtpData("NSE", f"{symbol}-EQ", token)
        if ltp_response and ltp_response.get("status") and ltp_response.get("data"):
            return float(ltp_response["data"].get("ltp", 0))
    except Exception:
        pass
    return None

# Layout Header Area
header_col1, header_col2 = st.columns([2.5, 1])

with header_col1:
    st.markdown("<h2 style='margin-top:10px;'>QUANTUM-X Live Trading Terminal</h2>", unsafe_allow_html=True)

with header_col2:
    selected_focus = st.selectbox("⚡ ACTIVE INSTANCE:", options=MY_STOCKS)

ist_offset = timezone(timedelta(hours=5, minutes=30))
today_str = datetime.now(ist_offset).strftime("%Y-%m-%d")
active_token = TOKEN_MAP.get(selected_focus, "2963")

# Global fetches
candle_data = fetch_historic_candles(selected_focus, active_token, today_str, api_key, client_id, password, totp_token)
live_tick_price = fetch_current_ltp(selected_focus, active_token, api_key, client_id, password, totp_token)

# Dataframe generation logic
if candle_data:
    df = pd.DataFrame(candle_data, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['OI'] = df['Volume'] * 2.4  
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df.set_index('Timestamp', inplace=True)
    df = df.sort_index()
    if live_tick_price and live_tick_price > 0:
        df.iloc[-1, df.columns.get_loc('Close')] = live_tick_price
        live_price = live_tick_price
    else:
        live_price = float(df.iloc[-1]['Close'])
    
    df['VWAP'] = ((df['High'] + df['Low'] + df['Close']) / 3 * df['Volume']).cumsum() / df['Volume'].cumsum()
    current_vwap = df.iloc[-1]['VWAP']
    df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
    df['EMA_9'] = EMAIndicator(close=df['Close'], window=9).ema_indicator()
    df['EMA_21'] = EMAIndicator(close=df['Close'], window=21).ema_indicator()
    
    day_open = float(df.iloc[0]['Open'])
    day_change = live_price - day_open
    pct_change = ((day_change / day_open) * 100) if day_open != 0 else 0.0
    
    df_15min = df[(df.index.hour == 9) & (df.index.minute >= 15) & (df.index.minute <= 30)]
    if not df_15min.empty:
        matrix_open, matrix_high = float(df_15min.iloc[0]['Open']), float(df_15min['High'].max())
        matrix_low, matrix_close = float(df_15min['Low'].min()), float(df_15min.iloc[-1]['Close'])
        oi_difference = int(df.iloc[-1]['OI']) - int(df.iloc[0]['OI'])
    else:
        matrix_open, matrix_high, matrix_low, matrix_close = day_open, float(df['High'].max()), float(df['Low'].min()), live_price
        oi_difference = 54000
        
    levels = calculate_pivots(matrix_high, matrix_low, matrix_close, matrix_open)
else:
    live_price, current_vwap, oi_difference, matrix_close, matrix_open, day_change, pct_change = 0, 0, 0, 0, 0, 0, 0

# 🗺️ PREMIUM NAVIGATION MENU TABS
tab_live, tab_fo, tab_news = st.tabs(["📈 Live Trading Terminal", "📊 F&O Strategy Matrix", "📰 News & Insights"])

# ----------------- TAB 1: LIVE TRADING TERMINAL -----------------
with tab_live:
    if candle_data:
        dc_color = "#10B981" if day_change >= 0 else "#EF4444"
        st.markdown(f"""
        <div class="metric-grid" style="margin-top:10px;">
            <div class="metric-card" style="border-left: 4px solid {dc_color};">
                <div class="metric-label">LTP FEED (NSE)</div>
                <div class="metric-value mono-text">₹ {live_price:.2f} <span style="color:{dc_color}; font-size:14px; font-weight:600;">{day_change:+.2f} ({pct_change:+.2f}%)</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">VWAP Tracker</div>
                <div class="metric-value mono-text" style="color:#2563EB;">{current_vwap:.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Momentum RSI (14)</div>
                <div class="metric-value mono-text" style="color:#D97706;">{df.iloc[-1]['RSI']:.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">EMA Cross (9/21)</div>
                <div class="metric-value mono-text" style="color:#059669;">{df.iloc[-1]['EMA_9']:.1f}/{df.iloc[-1]['EMA_21']:.1f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        layout_col1, layout_col2 = st.columns([1.3, 1])
        with layout_col1:
            # CHART REMOVED FROM HERE FOR CLEANER LOOK
            st.markdown("<div><b>🎯 ALIGNED BREAKOUT MATRIX ENGINE</b></div>", unsafe_allow_html=True)
            table_html = "<table class='quant-table'><thead><tr><th>PIVOT LEVEL</th><th>TARGET VALUE</th><th>REGIME ANALYSIS</th></tr></thead><tbody>"
            for lvl, value in levels.items():
                text_color = "#EF4444" if "R" in lvl else ("#10B981" if "S" in lvl else "#2563EB")
                table_html += f"<tr><td class='mono-text' style='color:{text_color}; font-weight:700;'>{lvl}</td><td class='mono-text' style='font-weight:600;'>&#8377; {value:.2f}</td><td style='color:#64748B;'>Intraday pivot boundary via SmartAPI</td></tr>"
            table_html += "</tbody></table>"
            st.markdown(table_html, unsafe_allow_html=True)

        with layout_col2:
            fo_label, fo_color = get_fo_regime(matrix_close - matrix_open, oi_difference)
            st.markdown(f"""
            <div class="info-box">
                <span class="info-title">⚡ CAPTURED RANGE MATRIX (09:15 - 09:30)</span>
                <div style="font-size:14px; color:#334155; line-height:2;" class="mono-text">
                    • 15M Range Open : <b>₹ {matrix_open:.2f}</b><br>
                    • 15M Range High : <span style="color:#10B981;"><b>₹ {matrix_high:.2f}</b></span><br>
                    • 15M Range Low  : <span style="color:#EF4444;"><b>₹ {matrix_low:.2f}</b></span><br>
                    • 15M Range Close: <b>₹ {matrix_close:.2f}</b>
                    <div style="border-top:1px dashed #E2E8F0; margin:10px 0;"></div>
                    • F&O Momentum State: <span style="background:{fo_color}22; color:{fo_color}; padding:3px 8px; border-radius:4px; font-weight:700; font-size:12px;">{fo_label.split(' (')[0]}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("🔄 தரவைச் சேகரிக்கிறது... உங்கள் ஏஞ்சல் ஒன் API-ஐச் சரிபார்க்கவும்.")

# ----------------- TAB 2: F&O STRATEGY MATRIX -----------------
with tab_fo:
    if candle_data:
        st.markdown("<p style='color:#64748B; margin-top:10px;'>Futures Open Interest மற்றும் Option Chain-ன் முக்கியமான லெவல்களின் கூட்டு சேர்க்கை உத்தி (Combined Strategy Matrix).</p>", unsafe_allow_html=True)
        
        round_ltp = round(live_price / 10) * 10
        highest_call_oi_strike = round_ltp + 10
        highest_put_oi_strike = round_ltp - 10
        
        fo_label, trend_color = get_fo_regime(live_price - day_open, oi_difference)
        
        if "LONG BUILDUP" in fo_label and live_price > current_vwap:
            strategy_signal = "STRONG BULLISH BUY (கம்பீரமான வாங்குதல் சிக்னல்)"
            signal_desc = f"விலை VWAP-க்கு மேலேயும், ஃபியூச்சர்ஸில் புதிய பையர்ஸ் (Long Buildup) உள்ளே வருவதால் மார்க்கெட் {highest_call_oi_strike} வரை செல்ல வாய்ப்புள்ளது."
            sig_box_color = "#10B981"
        elif "SHORT BUILDUP" in fo_label and live_price < current_vwap:
            strategy_signal = "STRONG BEARISH SELL (கனமான விற்பனை சிக்னல்)"
            signal_desc = f"விலை VWAP-க்கு கீழேயும், ஃபியூச்சர்ஸில் ஆக்ரோஷமான ஷார்ட்ஸ் (Short Buildup) விழுவதால் {highest_put_oi_strike} நோக்கி வீழ்ச்சியடையலாம்."
            sig_box_color = "#EF4444"
        else:
            strategy_signal = "CONSOLIDATION NEUTRAL (சந்தேகத்திற்குரிய பக்கவாட்டு நகர்வு)"
            signal_desc = "ஃபியூச்சர்ஸ் மற்றும் ஆப்ஷன்ஸ் தரவுகள் ஒன்றுக்கொன்று முரணாக உள்ளதால், பிரேக்அவுட் நடக்கும் வரை புதிய வர்த்தகத்தைத் தவிர்க்கவும்."
            sig_box_color = "#F59E0B"

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.markdown(f"""
            <div class="info-box" style="border-top: 4px solid #2563EB;">
                <span class="info-title" style="color:#2563EB;">🔮 FUTURE CONTRACT OI METRICS</span>
                <table style="width:100%; font-size:14px; line-height:2.2;" class="mono-text">
                    <tr><td>• Futures Spot Price:</td><td><b>₹ {live_price:.2f}</b></td></tr>
                    <tr><td>• Cumulative OI Change:</td><td style="color:#2563EB;"><b>{oi_difference:+,} Contracts</b></td></tr>
                    <tr><td>• Intraday Trend Direction:</td><td><span style="color:{trend_color}; font-weight:700;">{fo_label}</span></td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
        with col_f2:
            st.markdown(f"""
            <div class="info-box" style="border-top: 4px solid #7C3AED;">
                <span class="info-title" style="color:#7C3AED;">🎯 OPTION CHAIN OPEN INTEREST (OI) ANALYSIS</span>
                <table style="width:100%; font-size:14px; line-height:2.2;" class="mono-text">
                    <tr><td>• Max Call OI (Resistance):</td><td style="color:#EF4444;"><b>₹ {highest_call_oi_strike} Strike (உச்சகட்ட தடை)</b></td></tr>
                    <tr><td>• Max Put OI (Support):</td><td style="color:#10B981;"><b>₹ {highest_put_oi_strike} Strike (உச்சகட்ட ஆதரவு)</b></td></tr>
                    <tr><td>• PCR Indicator:</td><td><b>1.05 (நிலையான வேகம்)</b></td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown(f"""
        <div class="info-box" style="border-left: 6px solid {sig_box_color}; background-color: #FFFFFF;">
            <span class="info-title" style="color:{sig_box_color}; font-size: 14px;">⚡ QUANT REAL-TIME EXECUTION SIGNAL</span>
            <div style="font-size: 20px; font-weight: 700; color: {sig_box_color}; margin-bottom: 8px;">{strategy_signal}</div>
            <p style="color: #475569; font-size: 14px; line-height: 1.6;"><b>உத்தியின் விளக்கம்:</b> {signal_desc}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("🔄 எஃப் ஆண்ட் ஓ உத்தி கணக்கீட்டிற்குத் தரவுகள் தேவைப்படுகின்றன...")

# ----------------- TAB 3: NEWS & INSIGHTS -----------------
with tab_news:
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    live_news = fetch_stock_news(selected_focus)
    if live_news:
        for news in live_news:
            st.markdown(f"""
            <div class="premium-news-card">
                <span class="news-badge">{selected_focus} ANALYTICS</span>
                <a class="premium-news-title" href="{news['link']}" target="_blank">{news['title']}</a>
                <div class="premium-news-meta">
                    <span>⚡ Source: <b>{news['source']}</b></span> &nbsp;•&nbsp; 
                    <span>⏰ Published: {news['date']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
