import requests
import pandas as pd
import os
import json
import plotly.graph_objs as go
import plotly.io as pio

BOT_TOKEN = "8142201280:AAH9KCcOZXH5XvlvPOPKmvPMy9pKmgPqAFs"
CHAT_ID = "-1002605021077"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.get(url, params=params, timeout=5)
    except Exception as e:
        print(f"Telegram error: {e}")

def fetch_price_data(symbol, interval='1h', limit=150):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'n_trades', 'taker_base_vol',
            'taker_quote_vol', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df[['timestamp', 'high', 'low', 'close']]
    except:
        return None

def calculate_williams_r(df, period=14):
    df['WR'] = (
        (df['high'].rolling(period).max() - df['close']) /
        (df['high'].rolling(period).max() - df['low'].rolling(period).min())
    ) * -100
    return df

def calculate_atr(df, period=14):
    df['H-L'] = df['high'] - df['low']
    df['H-C'] = abs(df['high'] - df['close'].shift())
    df['L-C'] = abs(df['low'] - df['close'].shift())
    df['TR'] = df[['H-L', 'H-C', 'L-C']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=period).mean()
    return df

def generate_signal(df):
    df = df.dropna(subset=['ATR', 'WR'])
    if df.empty:
        return None
    latest = df.iloc[-1]
    entry = latest['close']
    atr = latest['ATR']
    wr = latest['WR']

    if wr < -95:
        signal = "BUY"
        tp1 = entry + atr * 1.5
        tp2 = entry + atr * 3
        sl = entry - atr
    elif wr > -5:
        signal = "SELL"
        tp1 = entry - atr * 1.5
        tp2 = entry - atr * 3
        sl = entry + atr
    else:
        return None

    return {
        "signal": signal,
        "entry": round(entry, 4),
        "tp1": round(tp1, 4),
        "tp2": round(tp2, 4),
        "sl": round(sl, 4),
        "wr": round(wr, 2)
    }

def plot_signal_chart(df, signal_info, symbol):
    df = df.tail(50)
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['close'], high=df['high'],
        low=df['low'], close=df['close'],
        name='Price'
    ))
    for level, color in [
        ('entry', 'blue'), ('tp1', 'green'),
        ('tp2', 'green'), ('sl', 'red')
    ]:
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=[signal_info[level]]*len(df),
            mode='lines', name=level.upper(), line=dict(color=color)
        ))

    fig.update_layout(title=f'{symbol} Signal Chart', height=500, template='plotly_dark')
    path = f'static/{symbol}.html'
    pio.write_html(fig, path, auto_open=False)
    return path

def log_open_signal(symbol, signal_info):
    path = "signal_log.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.load(f)
    else:
        data = []
    # Kiểm tra trùng
    for d in data:
        if d["symbol"] == symbol and d["signal"] == signal_info["signal"]:
            return  # không ghi lại nếu đang theo dõi
    signal_info["symbol"] = symbol
    data.append(signal_info)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
