import streamlit as st
import requests
from bs4 import BeautifulSoup
import yfinance as yf
import streamlit.components.v1 as components
import plotly.graph_objects as go
import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Terminal",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. SESSION STATE SETUP ---
if 'active_view' not in st.session_state:
    st.session_state['active_view'] = "Bitcoin" 
if 'active_chart' not in st.session_state:
    st.session_state['active_chart'] = "COINBASE:BTCUSD"
if 'dark_mode' not in st.session_state:
    st.session_state['dark_mode'] = True

# --- 3. THEME LOGIC (LOADED FIRST) ---
# We put this at the top to ensure variables exist before UI draws
def set_theme():
    # Toggle button in sidebar (Primary)
    with st.sidebar:
        st.title("💠 Callums Terminal")
        st.caption("v16.2 Stable")
        mode = st.checkbox("🌙 Dark Mode", value=st.session_state['dark_mode'], key="sidebar_theme_toggle")
    
    # Backup Toggle in Main Area (In case sidebar is hidden/broken)
    # This ensures you can always see the button.
    with st.expander("⚙️ Settings & Theme (Click if Sidebar is hidden)", expanded=False):
        st.write("Use this if you cannot see the sidebar.")
        mode_backup = st.checkbox("🌙 Enable Dark Mode", value=mode, key="backup_theme_toggle")
        
    # Sync states
    if mode != mode_backup:
        mode = mode_backup
    
    st.session_state['dark_mode'] = mode

    if mode:
        return {
            "bg": "#0E1117", "text": "#F3F4F6", "card_bg": "#1F2937", 
            "border": "#374151", "shadow": "rgba(0,0,0,0.3)",
            "tv_theme": "dark", "tab_active": "#F3F4F6", "tab_inactive": "#9CA3AF"
        }
    else:
        return {
            "bg": "#F3F4F6", "text": "#111827", "card_bg": "#FFFFFF", 
            "border": "#E5E7EB", "shadow": "rgba(0,0,0,0.05)",
            "tv_theme": "light", "tab_active": "#111827", "tab_inactive": "#6B7280"
        }

theme = set_theme()

# --- 4. CSS INJECTION ---
st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
        
        /* Global Reset */
        .stApp {{ background-color: {theme['bg']}; color: {theme['text']}; font-family: 'Inter', sans-serif; }}
        
        /* Mobile-Friendly Container */
        .block-container {{
            padding-top: 1rem !important;
            padding-bottom: 3rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }}
        @media (min-width: 768px) {{
            .block-container {{
                padding-left: 2rem !important;
                padding-right: 2rem !important;
            }}
        }}

        /* Sidebar Styling */
        [data-testid="stSidebar"] {{ 
            background-color: {theme['card_bg']}; 
            border-right: 1px solid {theme['border']};
        }}
        [data-testid="stSidebar"] * {{
            color: {theme['text']} !important;
        }}

        /* Typography */
        h1, h2, h3, p, span, div {{ color: {theme['text']}; }}
        
        /* Buttons */
        div.stButton > button {{
            background-color: {theme['card_bg']};
            color: {theme['text']};
            border: 1px solid {theme['border']};
            border-radius: 8px;
        }}
        button[kind="primary"] {{
            background-color: {theme['text']} !important;
            color: {theme['bg']} !important;
            border: none;
        }}

        /* Cards */
        .terminal-card {{
            background-color: {theme['card_bg']}; 
            border: 1px solid {theme['border']}; 
            border-radius: 12px;
            padding: 20px; 
            margin-bottom: 15px;
            box-shadow: 0 4px 6px -1px {theme['shadow']};
        }}
        
        /* Metrics */
        .metric-val {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 24px;
            font-weight: 700;
            color: {theme['text']};
        }}
    </style>
""", unsafe_allow_html=True)

# --- 5. DATA FUNCTIONS ---

@st.cache_data(ttl=60)
def get_market_data(tickers_dict):
    try:
        data = {}
        for name, symbol in tickers_dict.items():
            if not symbol: continue 
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d", interval="1m")
                if hist.empty: hist = ticker.history(period="2d")
                if not hist.empty:
                    latest = hist['Close'].iloc[-1]
                    open_p = hist['Open'].iloc[0] if len(hist) > 1 else latest
                    change = ((latest - open_p) / open_p) * 100
                    data[name] = (latest, change)
                else: data[name] = (0.0, 0.0)
            except: data[name] = (0.0, 0.0)
        return data
    except: return None

def get_symbol_details(key):
    key_upper = key.upper()
    icon = "📈"
    if "BTC" in key_upper: icon = "₿"
    elif "ETH" in key_upper: icon = "Ξ"
    elif "EUR" in key_upper: icon = "💶"
    elif "USD" in key_upper: icon = "💵"
    elif "GOLD" in key_upper: icon = "⚱️"
    elif "NVDA" in key_upper: icon = "🤖"
    return icon

def render_ticker_grid(data):
    if not data: return
    tv_map = {"BTC": "COINBASE:BTCUSD", "ETH": "COINBASE:ETHUSD", "SOL": "COINBASE:SOLUSD", "EUR": "FX:EURUSD", "GBP": "FX:GBPUSD", "JPY": "FX:USDJPY", "CHF": "FX:USDCHF", "CAD": "FX:USDCAD", "AUD": "FX:AUDUSD", "NZD": "FX:NZDUSD", "DXY": "TVC:DXY", "GOLD": "OANDA:XAUUSD", "OIL": "TVC:USOIL", "NVDA": "NASDAQ:NVDA", "TSLA": "NASDAQ:TSLA", "AAPL": "NASDAQ:AAPL", "SPX": "OANDA:SPX500USD", "NDX": "OANDA:NAS100USD"}
    
    # Responsive Grid Strategy
    cols = st.columns(6) 
    for i, (key, (price, change)) in enumerate(data.items()):
        icon = get_symbol_details(key)
        arrow = "▲" if change >= 0 else "▼"
        price_str = f"${price:,.0f}" if price > 100 else f"${price:.4f}"
        label = f"{icon} {key}\n{price_str} {arrow} {change:.2f}%"
        
        with cols[i % 6]:
            if st.button(label, key=f"btn_{key}", use_container_width=True):
                clean_key = key.split("-")[0] if "-" in key else key
                tv_code = tv_map.get(clean_key, tv_map.get(key, "COINBASE:BTCUSD"))
                st.session_state['active_chart'] = tv_code
                st.session_state['active_view'] = "Charts"
                st.rerun()

@st.cache_data(ttl=300)
def get_crypto_fng():
    try: return int(requests.get("https://api.alternative.me/fng/?limit=1").json()['data'][0]['value'])
    except: return 50

@st.cache_data(ttl=300)
def get_macro_fng():
    try:
        vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
        score = 100 - ((vix - 10) * 3)
        return max(0, min(100, int(score))), round(vix, 2)
    except: return 50, 0

def render_gauge(value, title, theme_text_color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value, title={'text': title, 'font': {'size': 14, 'color': theme_text_color}},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': theme_text_color}, 
               'steps': [{'range': [0, 25], 'color': "#EF4444"}, {'range': [25, 75], 'color': "#6B7280"}, {'range': [75, 100], 'color': "#10B981"}]}
    ))
    fig.update_layout(height=180, margin=dict(l=20, r=20, t=30, b=20), paper_bgcolor='rgba(0,0,0,0)', font={'family': "Inter"})
    st.plotly_chart(fig, use_container_width=True)

def render_chart(symbol, theme_mode):
    html = f"""
    <div class="tradingview-widget-container" style="height:500px;border-radius:12px;overflow:hidden;box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
      <div id="tradingview_{symbol}" style="height:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{"autosize": true, "symbol": "{symbol}", "interval": "D", "timezone": "Etc/UTC", "theme": "{theme_mode}", "style": "1", "locale": "en", "toolbar_bg": "#f1f3f6", "enable_publishing": false, "allow_symbol_change": true, "container_id": "tradingview_{symbol}"}});
      </script>
    </div>
    """
    components.html(html, height=500)

def render_economic_calendar(timezone_id):
    calendar_url = f"https://sslecal2.investing.com?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous&features=datepicker,timezone&countries=5,4,72,35,25,6,43,12,37&calType=week&timeZone={timezone_id}&lang=1&importance=3"
    html = f"""
    <div style="border: 1px solid #E5E7EB; border-radius: 12px; overflow: hidden; height: 600px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
        <iframe src="{calendar_url}" width="100%" height="600" frameborder="0" allowtransparency="true"></iframe>
    </div>
    """
    components.html(html, height=600)

# --- 6. AI ENGINE ---
@st.cache_data(ttl=600) 
def get_rss_news(query):
    try:
        url = f"https://news.google.com/rss/search?q={query}+when:1d&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.content, features="html.parser")
        items = soup.findAll('item')
        news_text = ""
        for item in items[:15]: 
            title = item.find('title').text if item.find('title') else "No Title"
            news_text += f"- {title}\n"
        return news_text if news_text else "No recent news found."
    except Exception as e: return f"News Feed Error: {str(e)}"

def resolve_best_model(api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        if 'error' in data: return None, data['error']['message']
        valid_models = [m['name'].replace("models/", "") for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        preferred = ["gemini-1.5-flash", "gemini-1.0-pro", "gemini-pro"]
        for p in preferred:
            if p in valid_models: return p, "OK"
        return (valid_models[0], "OK") if valid_models else (None, "No valid models")
    except Exception as e: return None, str(e)

@st.cache_data(ttl=3600, show_spinner="Analyzing...") 
def generate_report(data_dump, mode, api_key):
    if not api_key: return "⚠️ Please enter your Google API Key in the sidebar."
    clean_key = api_key.strip()
    active_model, status = resolve_best_model(clean_key)
    if not active_model: return f"❌ Error: {status}"
    
    headers = {'Content-Type': 'application/json'}
    safety_settings = [{"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"}]
    generation_config = {"maxOutputTokens": 2500}

    if mode == "BTC":
        prompt = f"""ROLE: Crypto Strategist. TASK: Bitcoin briefing. DATA: {data_dump}. OUTPUT: ### ⚡️ LIVE PULSE\n### 🏦 FLOWS\n### 🔮 SCENARIOS"""
    elif mode == "GEO":
        prompt = f"""ROLE: Risk Analyst. TASK: Global threats. DATA: {data_dump}. OUTPUT: ### 🌍 THREAT MATRIX\n### ⚔️ FLASHPOINTS\n### 🛡 MARKET IMPACT"""
    else: # FX
        prompt = f"""ROLE: FX Strategist. TASK: Detailed Outlook for 7 Major Pairs. DATA: {data_dump}. OUTPUT: **💵 DXY**\n---\n### 🇪🇺 EUR/USD\n### 🇬🇧 GBP/USD\n### 🇯🇵 USD/JPY\n### 🇨🇭 USD/CHF\n### 🇦🇺 AUD/USD\n### 🇨🇦 USD/CAD\n### 🇳🇿 NZD/USD"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{active_model}:generateContent?key={clean_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "safetySettings": safety_settings, "generationConfig": generation_config}
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        return r.json()['candidates'][0]['content']['parts'][0]['text'].replace("$","USD ") if 'candidates' in r.json() else f"❌ Error: {r.json().get('error', {}).get('message', 'Unknown')}"
    except Exception as e: return f"System Error: {str(e)}"

# --- 7. SIDEBAR EXTRAS ---
with st.sidebar:
    st.markdown(f"<div style='font-family: JetBrains Mono; font-size: 12px; color: {theme['text']}; margin-bottom: 20px;'>{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</div>", unsafe_allow_html=True)
    st.markdown("""<div style='margin-bottom: 20px;'><span class='status-dot'></span><span style='font-size: 14px; font-weight: 600; color: #059669;'>SYSTEM ONLINE</span></div>""", unsafe_allow_html=True)
    
    api_key = None
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"].strip()
            st.success("🔑 API Key Active")
        else:
            api_key = st.text_input("Enter API Key", type="password")
    except:
        api_key = st.text_input("Enter API Key", type="password")
    if api_key: api_key = api_key.strip()
    
    st.markdown("---")
    st.subheader("Settings")
    tz_map = {"London (GMT)": 15, "New York (EST)": 8, "Tokyo (JST)": 18}
    selected_tz = st.selectbox("Timezone:", list(tz_map.keys()), index=0)

# --- 8. MAIN DASHBOARD ---
st.markdown("## 🖥️ MARKET OVERVIEW")

col_sel, col_space = st.columns([1, 2])
with col_sel:
    selected_market = st.selectbox("Select Asset Class:", ["Standard", "Crypto", "Forex", "Tech Stocks", "Indices"], index=0, label_visibility="collapsed")

market_map = {
    "Standard": {"BTC": "BTC-USD", "EUR": "EURUSD=X", "USD": "DX-Y.NYB", "GOLD": "GC=F", "OIL": "CL=F", "SPX": "^GSPC"},
    "Crypto": {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "XRP": "XRP-USD", "DOGE": "DOGE-USD", "ADA": "ADA-USD"},
    "Forex": {"EUR": "EURUSD=X", "GBP": "GBPUSD=X", "JPY": "JPY=X", "CHF": "CHF=X", "CAD": "CAD=X", "AUD": "AUDUSD=X"},
    "Tech Stocks": {"NVDA": "NVDA", "TSLA": "TSLA", "AAPL": "AAPL", "MSFT": "MSFT", "GOOG": "GOOG", "AMZN": "AMZN"},
    "Indices": {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX", "FTSE": "^FTSE", "DAX": "^GDAXI"}
}
active_tickers = market_map[selected_market]
market_data = get_market_data(active_tickers)
render_ticker_grid(market_data)

st.write("") 

nav_options = ["Bitcoin", "Currencies", "Geopolitics", "Calendar", "Charts"]
cols = st.columns(len(nav_options))
for i, option in enumerate(nav_options):
    if cols[i].button(option, use_container_width=True, type="primary" if st.session_state['active_view'] == option else "secondary"):
        st.session_state['active_view'] = option
        st.rerun()

st.markdown("---")

view = st.session_state['active_view']

if view == "Bitcoin":
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown("### Market Sentiment")
        btc_fng = get_crypto_fng()
        st.markdown(f"<div class='terminal-card' style='text-align: center;'><div class='metric-val'>{btc_fng}</div><div style='font-size: 12px; color: {theme['text']};'>Fear & Greed Index</div></div>", unsafe_allow_html=True)
        render_gauge(btc_fng, "", theme['text'])
        
    with col_b:
        st.markdown("📡 Bitcoin Briefing")
        if st.button("GENERATE REPORT", type="primary"):
            raw_news = ""
            with st.spinner("Scanning Institutional Feeds..."):
                raw_news = get_rss_news("Bitcoin crypto market")
            st.info("⚡ Analyzing Market Structure...")
            report = generate_report(raw_news, "BTC", api_key)
            st.session_state['btc_rep'] = report
            st.rerun()
        if 'btc_rep' in st.session_state:
            st.markdown(f'<div class="terminal-card">{st.session_state["btc_rep"]}</div>', unsafe_allow_html=True)

elif view == "Currencies":
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown("🌍 Macro Risk")
        macro_score, _ = get_macro_fng()
        st.markdown(f"<div class='terminal-card' style='text-align: center;'><div class='metric-val'>{macro_score}</div><div style='font-size: 12px; color: {theme['text']};'>Risk Appetite Score</div></div>", unsafe_allow_html=True)
        render_gauge(macro_score, "", theme['text'])
    with col_b:
        st.markdown("### 💱 FX Strategy")
        if st.button("GENERATE FX OUTLOOK", type="primary"):
            raw_news = ""
            with st.spinner("Aggregating Central Bank Data..."):
                raw_news += get_rss_news("EURUSD GBPUSD USDJPY AUDUSD USDCAD forex")
            st.info("### ⚡ Synthesizing Analysis...")
            report = generate_report(raw_news, "FX", api_key)
            st.session_state['fx_rep'] = report
            st.rerun()
        if 'fx_rep' in st.session_state:
            st.markdown(f'<div class="terminal-card">{st.session_state["fx_rep"]}</div>', unsafe_allow_html=True)

elif view == "Geopolitics":
    st.markdown("### 🌐 Analysing global events")
    if st.button("RUN INTEL SCAN", type="primary"):
        raw_news = ""
        with st.spinner("Parsing Classified Wires..."):
            raw_news += get_rss_news("Geopolitics War Oil Gold Economy")
        st.info("⚡ Assessing Strategic Risks...")
        report = generate_report(raw_news, "GEO", api_key)
        st.session_state['geo_rep'] = report
        st.rerun()
    if 'geo_rep' in st.session_state:
        st.markdown(f'<div class="terminal-card">{st.session_state["geo_rep"]}</div>', unsafe_allow_html=True)

elif view == "Calendar":
    st.markdown("### 📅 Economic Calendar")
    render_economic_calendar(tz_map[selected_tz])

elif view == "Charts":
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"{st.session_state['active_chart']}")
        render_chart(st.session_state['active_chart'], theme['tv_theme'])
    with col2:
        asset_map = {
            "Bitcoin (BTC/USD)": "COINBASE:BTCUSD", "Ethereum (ETH/USD)": "COINBASE:ETHUSD",
            "Ripple (XRP/USD)": "COINBASE:XRPUSD", "Gold (XAU/USD)": "OANDA:XAUUSD",
            "Crude Oil (WTI)": "TVC:USOIL", "Dollar Index (DXY)": "TVC:DXY",
            "EUR / USD": "FX:EURUSD", "GBP / USD": "FX:GBPUSD", "USD / JPY": "FX:USDJPY",
            "USD / CHF": "FX:USDCHF", "AUD / USD": "FX:AUDUSD", "USD / CAD": "FX:USDCAD",
            "NZD / USD": "FX:NZDUSD"
        }
        default_ix = 0
        current_val = st.session_state['active_chart']
        vals = list(asset_map.values())
        if current_val in vals: default_ix = vals.index(current_val)
        selected_label = st.selectbox("Quick Switch:", list(asset_map.keys()), index=default_ix, label_visibility="collapsed")
        
        if asset_map[selected_label] != current_val:
            st.session_state['active_chart'] = asset_map[selected_label]
            st.rerun()
