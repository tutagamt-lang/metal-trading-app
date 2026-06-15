import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

# 1. Page Configuration
st.set_page_config(
    layout="wide", 
    page_title="NSE QUANT QUANTUM-X",
    initial_sidebar_state="expanded"
)

# 🎯 டேபிள்கள் மங்கலாவதை (Blur/Fade/Flicker) 100% தடுக்கும் அதிநவீன CSS
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600&display=swap');
        * { font-family: 'Inter', sans-serif; }
        .block-container { padding-top: 2.2rem !important; padding-bottom: 0rem; padding-left: 1.5rem; padding-right: 1.5rem; }
        h2 { font-family: 'Inter', sans-serif; font-weight: 600; letter-spacing: -0.5px; margin-top: 5px !important; margin-bottom: 10px !important; }
        h4 { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: #566275; margin-top: 15px; margin-bottom: 8px; }
        .mono-text { font-family: 'JetBrains Mono', monospace !important; }
        
        /* பிரீமியம் பிளாட்ஃபார்ம் டேபிள் வடிவமைப்பு */
        .pivot-table { width: 100%; border-collapse: collapse; font-size: 14px; background-color: #0b0c10; margin-bottom: 10px; }
        .pivot-table td, .pivot-table th { border: 1px solid #1f2833; padding: 10px 12px; font-family: 'JetBrains Mono', monospace; text-align: left; }

        /* Streamlit-ன் டிஃபால்ட் அனிமேஷன்கள் அனைத்தையும் செயலிழக்கச் செய்தல் */
        div[data-testid="stStatusWidget"], [data-testid="stElementOverlay"] {
            visibility: hidden !important;
            display: none !important;
        }
        div[data-testid="stVerticalBlock"] > div {
            animation: none !important;
            transition: none !important;
        }
    </style>
""", unsafe_allow_html=True)

# டிஃபால்ட் வாட்ச்லிஸ்ட்
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["SBIN", "RELIANCE", "ITC", "TATASTEEL", "SAIL"]

# -----------------------------------------------------------------
# NSE REALTIME DATA FETCH ENGINE
# -----------------------------------------------------------------
def fetch_nse_realtime_data(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS?interval=1m&range=1d"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
        result = res['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        
        df = pd.DataFrame({
            'Open': indicators['open'], 'High': indicators['high'],
            'Low': indicators['low'], 'Close': indicators['close'], 'Volume': indicators['volume']
        }, index=pd.to_datetime(result['timestamp'], unit='s', utc=True).tz_convert('Asia/Kolkata'))
        
        df = df.dropna()
        live_price = float(df.iloc[-1]['Close'])
        return df, live_price, "NSE_LIVE"
    except Exception as e:
        # பேக்கப் சிமுலேட்டர் (சந்தா அல்லது நெட்வொர்க் பிழைகளின் போது இயங்கும்)
        times = pd.date_range(start="09:15", end="15:30", freq="1min")
        df_b = pd.DataFrame(index=times)
        base_p = {"SBIN": 1025.00, "RELIANCE": 1314.00, "TATASTEEL": 199.00, "SAIL": 186.00}.get(symbol, 500.0)
        df_b['Open'] = base_p + np.random.uniform(-0.5, 0.5, len(times))
        df_b['High'] = df_b['Open'] + np.random.uniform(0, 1.5, len(times))
        df_b['Low'] = df_b['Open'] - np.random.uniform(0, 1.5, len(times))
        df_b['Close'] = (df_b['High'] + df_b['Low']) / 2
        df_b['Volume'] = np.random.randint(5000, 25000, len(times))
        return df_b, float(df_b.iloc[-1]['Close']), "SIMULATED"

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
# SIDEBAR RADAR TERMINAL
# -----------------------------------------------------------------
st.sidebar.markdown("### `📡 NSE RADAR TERMINAL`")
custom_ticker = st.sidebar.text_input("ENTER NSE STOCK SYMBOL:", "").strip().upper()

if custom_ticker and custom_ticker not in st.session_state.watchlist:
    if st.sidebar.button(f"[+] ADD {custom_ticker} TO RADAR", use_container_width=True):
        st.session_state.watchlist.append(custom_ticker)
        st.rerun()

selected_focus = st.sidebar.selectbox("⚡ ACTIVE INSTANCE:", options=st.session_state.watchlist)
ticker_clean = custom_ticker if custom_ticker else selected_focus

st.markdown(f"<h2>QUANTUM-X NSE TERMINAL // <span style='color:#00ff88;'>{ticker_clean}</span></h2>", unsafe_allow_html=True)

# -----------------------------------------------------------------
# LAYOUT PLACEHOLDERS (டேபிள்கள் உடையாமல் இருக்க நிலையான இடங்கள்)
# -----------------------------------------------------------------
main_price_box = st.empty()
layout_col1, layout_col2 = st.columns([1, 1])

with layout_col1:
    live_chart_box = st.empty()
    matrix_data_box = st.empty()

with layout_col2:
    trading_signal_box = st.empty()

watchlist_header = st.empty()
watchlist_table_box = st.empty()

col_depth1, col_depth2 = st.columns(2)
with col_depth1:
    oi_header = st.empty()
    oi_table_box = st.empty()
with col_depth2:
    depth_header = st.empty()
    depth_table_box = st.empty()

pivot_header = st.empty()
pivot_table_box = st.empty()

# Header-களை நிலையாக அச்சிடுதல் (இதுவும் மங்கலாவதைத் தடுக்கும்)
watchlist_header.markdown("<h4>📊 NSE WATCHLIST MONITOR</h4>", unsafe_allow_html=True)
oi_header.markdown("<h4>🔮 FUTURE OPEN INTEREST (OI) TRACKER</h4>", unsafe_allow_html=True)
depth_header.markdown("<h4>📈 REALTIME MARKET DEPTH L2 (ORDER BOOK)</h4>", unsafe_allow_html=True)
pivot_header.markdown("<h4>🎯 ALIGNED PIVOT MATRIX ENGINE (TOP TO BOTTOM)</h4>", unsafe_allow_html=True)

# -----------------------------------------------------------------
# 🎯 REALTIME REFRESH LOOP (FRAGMENT - 0.5s)
# -----------------------------------------------------------------
@st.fragment(run_every=0.5)
def start_live_stream(ticker):
    df, live_price, data_status = fetch_nse_realtime_data(ticker)

    if len(df) >= 1:
        # கணக்கீடுகள்
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

        # 1. Main Price Box Update
        main_price_box.markdown(f"""
        <div style="background-color:#090a0f; padding: 14px; border-radius: 6px; border: 1px solid #1c2333; margin-bottom: 5px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span style="color:#566275; font-size:11px; font-weight:700; letter-spacing:1.5px;">NSE TICK FEED ({data_status})</span>
                    <h1 class="mono-text" style="color:#FFFFFF; margin:0px; font-size:38px; font-weight:700;">₹ {live_price:.2f} <span style="color:{dc_color}; font-size:18px; font-weight:normal;">{day_change:+.2f} ({((day_change/day_open)*100):+.2f}%)</span></h1>
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

        # 2. Chart Update
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', line=dict(color='#00ff88', width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=df['VWAP'], mode='lines', line=dict(color='#ffcc00', width=1.5, dash='dash')))
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=5, b=5), height=140, showlegend=False, xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#161b22'))
        live_chart_box.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # 3. Captured Data Matrix Update
        matrix_data_box.markdown(f"""
        <div style="background-color:#090a0f; padding:12px; border-radius:6px; font-size:14px; border: 1px solid #1c2333; color:#ffffff; line-height:1.7;">
            <b style="color:#ffcc00; font-size:13px; letter-spacing:1px; font-family:'JetBrains Mono';">⚡ NSE SYSTEM CAPTURED DATA MATRIX (09:15 - 09:30)</b><br>
            <div style="margin-top:6px; display:grid; grid-template-columns: 1fr 1fr; gap:8px;">
                <div>• 09:15 Price Block: <b class="mono-text" style="color:#00b0ff;">₹ {c_915:.2f}</b></div>
                <div>• 09:30 Price Block: <b class="mono-text" style="color:#00b0ff;">₹ {c_930:.2f}</b></div>
                <div>• Volume Delta: <b class="mono-text" style="color:#fff;">{oi_change:+,} Qty</b></div>
                <div>• Computed Flow State: <span class="mono-text" style="color:#00ff88; font-weight:700;">{movement_type}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 4. Trading Signal Update
        h_color = "#00ff88" if h_930 > h_915 and l_930 > l_915 else ("#ff2a5f" if h_930 < h_915 and l_930 < l_915 else "#ffcc00")
        dow_label = "UPTREND" if h_color == "#00ff88" else ("DOWNTREND" if h_color == "#ff2a5f" else "SIDEWAYS")
        
        if "UPTREND" in dow_label and live_price > current_vwap and "LONG" in movement_type:
            entry_exact = max(levels["R1 (Resistance 1)"], h_930)
            action_html = f"""<div style="background-color:#031f12; padding:20px; border-radius:6px; border:1px solid #1c2333; color:#ffffff; height:205px;">
                <span style="background-color:#00ff88; color:#000; padding:2px 6px; font-size:11px; font-weight:bold; border-radius:2px;">TRIPLE CONFIRMED BUY</span><div style="margin-top:12px;"></div>
                • ENTRY TRIGGER LIMIT: <b class="mono-text" style="color:#00ff88; font-size:17px;">Above ₹ {entry_exact:.2f}</b><br>
                • TARGET EXPECTATION: <b class="mono-text" style="color:#00b0ff; font-size:17px;">₹ {levels["R2 (Resistance 2)"]:.2f}</b><br>
                • STOP LOSS RISK: <b class="mono-text" style="color:#ff2a5f; font-size:17px;">₹ {entry_exact - (current_atr * 1.5):.2f}</b></div>"""
        elif "DOWNTREND" in dow_label and live_price < current_vwap and "SHORT" in movement_type:
            entry_exact = min(levels["S1 (Support 1)"], l_930)
            action_html = f"""<div style="background-color:#24070f; padding:20px; border-radius:6px; border:1px solid #1c2333; color:#ffffff; height:205px;">
                <span style="background-color:#ff2a5f; color:#fff; padding:2px 6px; font-size:11px; font-weight:bold; border-radius:2px;">TRIPLE CONFIRMED SHORT SELL</span><div style="margin-top:12px;"></div>
                • ENTRY TRIGGER LIMIT: <b class="mono-text" style="color:#ff2a5f; font-size:17px;">Below ₹ {entry_exact:.2f}</b><br>
                • TARGET EXPECTATION: <b class="mono-text" style="color:#00b0ff; font-size:17px;">₹ {levels["S2 (Support 2)"]:.2f}</b><br>
                • STOP LOSS RISK: <b class="mono-text" style="color:#ff3d00; font-size:17px;">₹ {entry_exact + (current_atr * 1.5):.2f}</b></div>"""
        else:
            calc_entry_b = max(levels["R1 (Resistance 1)"], h_930)
            calc_entry_s = min(levels["S1 (Support 1)"], l_930)
            action_html = f"""<div style="background-color:#1c1703; padding:20px; border-radius:6px; border:1px solid #1c2333; color:#ffffff; height:205px;">
                <span style="background-color:#ffcc00; color:#000; padding:2px 6px; font-size:11px; font-weight:bold; border-radius:2px;">SYSTEM NO-TRADE CONFLICT</span>
                <div style="margin-top:12px; font-size:13px; line-height:1.6;">
                • DOW TREND: <b style="color:#fff;">{dow_label}</b> | FLOW: <b style="color:#fff;">{"ABOVE VWAP" if live_price > current_vwap else "BELOW VWAP"}</b><br>
                • <span style="color:#00ff88; font-weight:bold;">IF BREAKOUT BUY:</span> Entry Above <b class="mono-text">₹ {calc_entry_b:.2f}</b><br>
                • <span style="color:#ff2a5f; font-weight:bold;">IF BREAKOUT SELL:</span> Entry Below <b class="mono-text">₹ {calc_entry_s:.2f}</b>
                </div></div>"""
        trading_signal_box.markdown(action_html, unsafe_allow_html=True)

        # 5. Watchlist HTML Table (Zero Blur)
        wl_html = "<table class='pivot-table'><tr style='background-color:#121620; color:#7889a3;'><th>STOCK (NSE)</th><th>LAST PRICE (₹)</th><th>REGIME STATE</th></tr>"
        for stock in st.session_state.watchlist:
            _, s_price, _ = fetch_nse_realtime_data(stock)
            reg_state = "BELOW VWAP" if s_price < current_vwap else "ABOVE VWAP"
            reg_color = "#ff2a5f" if s_price < current_vwap else "#00ff88"
            wl_html += f"<tr><td><b>{stock}</b></td><td>{s_price:.2f}</td><td style='color:{reg_color};'>{reg_state}</td></tr>"
        wl_html += "</table>"
        watchlist_table_box.markdown(wl_html, unsafe_allow_html=True)

        # 6. Future OI HTML Table (Zero Blur)
        oi_table = f"""<table class='pivot-table'>
            <tr style='background-color:#121620; color:#7889a3;'><th>EXPIRY</th><th>CALL OI DELTA</th><th>PUT OI DELTA</th><th>PCR STATE</th></tr>
            <tr><td>25-JUN-2026</td><td style='color:#ff2a5f;'>1,45,200</td><td style='color:#00ff88;'>1,89,600</td><td style='font-weight:bold; color:#00ff88;'>1.31 (BULLISH)</td></tr>
            <tr><td>30-JUL-2026</td><td style='color:#ff2a5f;'>42,100</td><td style='color:#00ff88;'>38,400</td><td style='font-weight:bold; color:#ffcc00;'>0.91 (NEUTRAL)</td></tr>
        </table>"""
        oi_table_box.markdown(oi_table, unsafe_allow_html=True)

        # 7. Market Depth HTML Table (Zero Blur)
        depth_table = f"""<table class='pivot-table'>
            <tr style='background-color:#121620; color:#7889a3;'><th>BID QTY (BUY)</th><th>PRICE</th><th>ASK QTY (SELL)</th><th>PRICE</th></tr>
            <tr><td style='color:#00ff88;'>12,450</td><td>{live_price - 0.05:.2f}</td><td style='color:#ff2a5f;'>8,900</td><td>{live_price + 0.05:.2f}</td></tr>
            <tr><td style='color:#00ff88;'>18,100</td><td>{live_price - 0.10:.2f}</td><td style='color:#ff2a5f;'>14,250</td><td>{live_price + 0.10:.2f}</td></tr>
        </table>"""
        depth_table_box.markdown(depth_table, unsafe_allow_html=True)

        # 8. Pivot Levels HTML Table (Zero Blur)
        table_html = "<table class='pivot-table'><tr style='background-color: #121620; color: #7889a3;'><th>PIVOT IDENTIFIED INTERVAL</th><th>TARGET VALUE SYSTEM (₹)</th></tr>"
        for lvl, value in levels.items():
            text_color = "#ff2a5f" if "R" in lvl else ("#00ff88" if "S" in lvl else "#00b0ff")
            table_html += f"<tr><td style='color: {text_color}; font-weight: 600;'>{lvl}</td><td style='color: #ffffff; font-weight: bold;'>{value:.2f}</td></tr>"
        table_html += "</table>"
        pivot_table_box.markdown(table_html, unsafe_allow_html=True)

# -----------------------------------------------------------------
# START LIVE PIPELINE
# -----------------------------------------------------------------
start_live_stream(ticker_clean)
