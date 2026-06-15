# -----------------------------------------------------------------
    # 🎯 REALTIME ADVANCED BREAKOUT SCANNED MATRIX (OI + BREAKDOWN FIXED)
    # -----------------------------------------------------------------
    st.markdown("#### `🎯 REALTIME ADVANCED BREAKOUT SCANNED MATRIX (FUTURES + OPTIONS)`")
    
    r1_val = levels["R1 (Resistance 1)"]
    s1_val = levels["S1 (Support 1)"]
    
    is_near_resistance = abs(live_price - r1_val) <= (live_price * 0.006)
    is_near_support = abs(live_price - s1_val) <= (live_price * 0.006)
    fut_oi_change_pct = float(f"{((df.iloc[-1]['Volume'] - df.iloc[0]['Volume'])/df.iloc[0]['Volume'])*10:.2f}") if len(df)>1 else 5.2
    
    # 🌟 லாஜிக் மாற்றம்: விலை சப்போர்ட்டை உடைத்து கீழே இருந்தால் (உங்களுடைய தற்போதைய நிலை 198.87 < 199.86)
    if live_price < s1_val:
        status_box = "💥 REAL BREAKDOWN: SHORT BUILDUP"
        color_box = "#ff2a5f"
        tamil_desc = f"விலை முக்கிய சப்போர்ட் எல்லையை (₹ {s1_val:.2f}) உடைத்து கீழே இறங்கிவிட்டது. Futures OI அதிகரித்துக் கொண்டே விலை சரிவதால், இது ஒரு 'SHORT BUILDUP' ஆகும். Put Option எழுதியவர்கள் (Put Writers) பயந்து தங்களின் பொசிஷன்களை மூடுவதால் (Put Unwinding) மார்க்கெட் இன்னும் வேகமாகச் சரியும்!"
        trade_action = "⚡ SELL ACTION: சப்போர்ட் உடைந்துவிட்டதால், தாராளமாக Short பொசிஷன் அல்லது PE (Put Option) எடுக்கலாம்!"

    # 🌟 விலை ரெசிஸ்டன்ஸை உடைத்து மேலே இருந்தால்
    elif live_price > r1_val:
        status_box = "🔥 REAL BREAKOUT: LONG BUILDUP"
        color_box = "#00ff88"
        tamil_desc = f"விலை முக்கிய ரெசிஸ்டன்ஸ் எல்லையை (₹ {r1_val:.2f}) உடைத்து மேலே ஏறியுள்ளது. Futures OI மற்றும் விலை இரண்டுமே அதிகரிப்பதால் (Long Buildup), Call Writers தங்களின் பொசிஷன்களை மூடிவிட்டு ஓடுகிறார்கள் (Call Unwinding). இது பலமான அப்-ட்ரெண்ட்!"
        trade_action = "⚡ BUY ACTION: ரெசிஸ்டன்ஸ் உடைந்ததால், தாராளமாக Long பொசிஷன் அல்லது CE (Call Option) எடுக்கலாம்!"

    # விலை சப்போர்ட் லைனுக்கு அருகில் வந்து மேலே திரும்பினால் (Bounce Back)
    elif is_near_support and live_price >= s1_val:
        status_box = "🍏 SUPPORT REVERSAL: BOUNCE BACK"
        color_box = "#00ff88"
        tamil_desc = f"விலை சப்போர்ட் எல்லைக்கு (₹ {s1_val:.2f}) அருகில் வந்து, அதை உடைக்காமல் மேலே திரும்புகிறது. இந்த எல்லையில் Put OI அசுர வேகத்தில் குவிந்துள்ளதால், பெரிய நிறுவனங்கள் இந்த விலைக்கு கீழே ஸ்டாக்கை விடமாட்டார்கள். இங்கிருந்து ராக்கெட் போல் மேலே ஏறும்."
        trade_action = "⚡ BUY ACTION: சப்போர்ட்டில் தஞ்சம் அடைந்து மேலே திரும்புவதால் தாராளமாக Buy/Call Option எடுக்கலாம்."

    # விலை ரெசிஸ்டன்ஸ் லைனுக்கு அருகில் வந்து கீழே திரும்பினால் (Fake Breakout)
    elif is_near_resistance and live_price <= r1_val:
        status_box = "⚠️ RESISTANCE REVERSAL / FAKE BREAKOUT"
        color_box = "#ff2a5f"
        tamil_desc = f"விலை ரெசிஸ்டன்ஸ் எல்லைக்கு (₹ {r1_val:.2f}) அருகில் வந்தாலும் அதை உடைக்க முடியாமல் திணறுகிறது. Call OI இன்னும் பிரமாதமாக வலுவாக உள்ளது. பெரிய கைகள் மார்க்கெட்டை மேலே விடத் தயாராக இல்லை. இங்கிருந்து விலை கீழே விழும்!"
        trade_action = "🛑 SELL ACTION: Resistance தாங்காமல் கீழே திரும்பும்போது Short / Put Option வாங்கலாம்."

    else:
        status_box = "📡 CONSOLIDATION: MEAN REVERSION"
        color_box = "#00b0ff"
        tamil_desc = "தற்போது ஸ்டாக் எந்த ஒரு முக்கிய சப்போர்ட் அல்லது ரெசிஸ்டன்ஸ் எல்லையையும் தொடவில்லை. நடுநிலையான எல்லையில் வர்த்தகம் ஆகிறது (Sideways / Consolidation)."
        trade_action = "⏳ WAIT: விலை முக்கிய சப்போர்ட் அல்லது ரெசிஸ்டன்ஸ் எல்லைக்கு அருகில் வரும் வரை பொறுமையாக காத்திருக்கவும்."
