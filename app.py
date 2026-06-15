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
st.set_page_config(layout="wide", page_title="QUANTUM-X Live Trading Terminal")
 
# 🎯 HIGH-CONTRAST CSS
st.markdown("""
    <style>
        .block-container { padding-top: 2rem; }
        .matrix-box { 
            background-color: #0d1117; 
            padding: 20px; 
            border-radius: 6px; 
            border: 1px solid #30363d; 
            margin-bottom: 20px;
        }
        /* எழுத்துக்களை வெண்மையாக மாற்ற கட்டாயப்படுத்தப்பட்ட ஸ்டைல் */
        .text-white { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)
 
# (மேலே உள்ள உங்கள் தரவு செயல்பாடுகள் அப்படியே இருக்கட்டும் - fetch_realtime_nse_data, get_oi_movement போன்றவை)
# ... [உங்கள் முந்தைய கோடின் செயல்பாடுகள் இங்கே தொடரும்] ...

# 🎯 REALTIME ADVANCED BREAKOUT SCANNED MATRIX (திருத்தப்பட்ட பகுதி)
st.markdown("#### `🎯 REALTIME ADVANCED BREAKOUT SCANNED MATRIX`")
    
r1_val = levels["R1 (Resistance 1)"]
s1_val = levels["S1 (Support 1)"]
    
# Logic (முந்தையது போலவே)
if live_price < s1_val:
    status_box = "💥 REAL BREAKDOWN: SHORT BUILDUP"
    color_box = "#ff2a5f"
    tamil_desc = f"விலை முக்கிய சப்போர்ட் எல்லையை (₹ {s1_val:.2f}) உடைத்து கீழே இறங்கிவிட்டது. இது ஒரு SHORT BUILDUP ஆகும்."
    trade_action = "⚡ SELL ACTION: சப்போர்ட் உடைந்துவிட்டதால், தாராளமாக Short பொசிஷன் எடுக்கலாம்!"
elif live_price > r1_val:
    status_box = "🔥 REAL BREAKOUT: LONG BUILDUP"
    color_box = "#00ff88"
    tamil_desc = f"விலை முக்கிய ரெசிஸ்டன்ஸ் எல்லையை (₹ {r1_val:.2f}) உடைத்து மேலே ஏறியுள்ளது. இது பலமான அப்-ட்ரெண்ட்!"
    trade_action = "⚡ BUY ACTION: ரெசிஸ்டன்ஸ் உடைந்ததால், தாராளமாக Long பொசிஷன் எடுக்கலாம்!"
else:
    status_box = "📡 CONSOLIDATION"
    color_box = "#00b0ff"
    tamil_desc = "தற்போது ஸ்டாக் ஒரு நடுநிலையான எல்லையில் வர்த்தகம் ஆகிறது."
    trade_action = "⏳ WAIT: விலை முக்கிய எல்லைக்கு வரும் வரை பொறுமையாக காத்திருக்கவும்."

# 🌟 திருத்தப்பட்ட UI Display (Color Forced to White)
st.markdown(f"""
<div class="matrix-box" style="border-left: 6px solid {color_box};">
    <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
        <span style="color: {color_box}; font-size: 16px; font-weight: bold;">{status_box}</span>
    </div>
    <div style="margin-bottom: 15px; font-size: 14px;" class="text-white">
        <strong style="color: #ffcc00;">📊 தமிழ் சந்தை விளக்கம்:</strong> {tamil_desc}
    </div>
    <div style="background-color: #161b22; padding: 12px; border-radius: 4px; font-size: 14px; color: {color_box}; font-weight: bold;">
        {trade_action}
    </div>
</div>
""", unsafe_allow_html=True)
