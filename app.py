import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import json
import os

st.set_page_config(page_title="Crypto KI App V10", layout="wide")

# =====================
# CONFIG
# =====================

COINS = {
    "Bitcoin": "bitcoin",
    "Ethereum": "ethereum",
    "Solana": "solana"
}

DATA_FILE = "trades.json"

# =====================
# STORAGE
# =====================

def load_trades():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_trades(trades):
    with open(DATA_FILE, "w") as f:
        json.dump(trades, f)

# =====================
# API
# =====================

@st.cache_data(ttl=120)
def get_price(coin):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
    return requests.get(url).json()[coin]["usd"]

@st.cache_data(ttl=120)
def get_chart(coin, days):
    url = f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart?vs_currency=usd&days={days}"
    data = requests.get(url).json()
    df = pd.DataFrame(data["prices"], columns=["time","price"])
    df["time"] = pd.to_datetime(df["time"], unit="ms")
    return df

# =====================
# INDICATORS
# =====================

def add_indicators(df):

    df["SMA20"] = df["price"].rolling(20).mean()
    df["SMA50"] = df["price"].rolling(50).mean()
    df["EMA20"] = df["price"].ewm(span=20).mean()

    delta = df["price"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100/(1+rs))

    return df

# =====================
# KI SIGNAL ENGINE
# =====================

def ai_signal(df):

    score = 0

    if df["SMA20"].iloc[-1] > df["SMA50"].iloc[-1]:
        score += 1

    if df["price"].iloc[-1] > df["EMA20"].iloc[-1]:
        score += 1

    if df["RSI"].iloc[-1] < 30:
        score += 1

    if df["RSI"].iloc[-1] > 70:
        score -= 1

    if score >= 2:
        return "BUY", score
    elif score <= -1:
        return "SELL", score
    return "HOLD", score

# =====================
# UI HEADER
# =====================

st.title("🤖 Crypto KI Strategy App V10")

coin_name = st.sidebar.selectbox("Coin", list(COINS.keys()))
days = st.sidebar.slider("Chart Tage", 7, 90, 30)
show_ind = st.sidebar.checkbox("Indicators anzeigen", True)

coin_id = COINS[coin_name]

# =====================
# LIVE PRICE
# =====================

price = get_price(coin_id)
st.metric("Live Preis USD", price)

# =====================
# DATA + CHART
# =====================

df = get_chart(coin_id, days)
df = add_indicators(df)

fig = go.Figure()
fig.add_trace(go.Scatter(x=df["time"], y=df["price"], name="Preis"))

if show_ind:
    fig.add_trace(go.Scatter(x=df["time"], y=df["SMA20"], name="SMA20"))
    fig.add_trace(go.Scatter(x=df["time"], y=df["SMA50"], name="SMA50"))
    fig.add_trace(go.Scatter(x=df["time"], y=df["EMA20"], name="EMA20"))

fig.update_layout(height=500)
st.plotly_chart(fig, use_container_width=True)

# =====================
# KI SIGNAL PANEL
# =====================

st.subheader("🧠 KI Signal")

signal, score = ai_signal(df)

if signal == "BUY":
    st.success(f"BUY Signal | Score {score}")
elif signal == "SELL":
    st.error(f"SELL Signal | Score {score}")
else:
    st.warning(f"HOLD | Score {score}")

# =====================
# STRATEGY BACKTEST
# =====================

st.subheader("🧪 Strategy Backtest")

if st.button("Backtest SMA Strategy"):

    cash = 1000
    coin_amt = 0

    for i in range(50, len(df)):

        if df["SMA20"].iloc[i] > df["SMA50"].iloc[i] and coin_amt == 0:
            coin_amt = cash / df["price"].iloc[i]
            cash = 0

        elif df["SMA20"].iloc[i] < df["SMA50"].iloc[i] and coin_amt > 0:
            cash = coin_amt * df["price"].iloc[i]
            coin_amt = 0

    final = cash if cash > 0 else coin_amt * df["price"].iloc[-1]

    st.info(f"Backtest Ergebnis: {round(final,2)} USD")

# =====================
# SL / TP TOOL
# =====================

st.subheader("🎯 StopLoss / TakeProfit")

entry = st.number_input("Entry", value=float(price))
sl = st.number_input("Stop Loss")
tp = st.number_input("Take Profit")

if entry > 0 and sl > 0 and tp > 0:
    risk = entry - sl
    reward = tp - entry
    st.write("Risk Reward:", round(reward/risk,2))

# =====================
# TRADE LOG
# =====================

st.subheader("💰 Trades")

t_type = st.selectbox("Typ", ["BUY","SELL"])
amt = st.number_input("Menge", 0.0)
tprice = st.number_input("Preis", value=float(price))

if st.button("Trade speichern"):
    trades = load_trades()
    trades.append({
        "coin": coin_name,
        "type": t_type,
        "amount": amt,
        "price": tprice
    })
    save_trades(trades)

trades = load_trades()
if trades:
    st.dataframe(pd.DataFrame(trades), use_container_width=True)

# =====================
# FOOTER
# =====================

st.caption("V10 KI Crypto App — Mobile Ready")
