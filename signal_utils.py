# === signal_utils.py ===
import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv
import logging

# === Cấu hình logging ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("signals.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# === Load biến môi trường ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# === Gửi tin nhắn Telegram ===
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    params = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.ok:
            logging.info("✅ Gửi Telegram thành công.")
        else:
            logging.warning("⚠️ Gửi Telegram thất bại.")
        return resp.ok
    except Exception as e:
        logging.error(f"❌ Lỗi gửi Telegram: {e}")
        return False

# === Ghi tín hiệu vào JSON ===
def log_open_signal(symbol, signal_info, filename="signal_log.json"):
    data = []
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                data = json.load(f)
            except:
                data = []
    signal_info["symbol"] = symbol
    signal_info["status"] = "OPEN"
    data.append(signal_info)
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    logging.info(f"📝 Đã lưu tín hiệu {symbol} vào {filename}")

# === Bitget Price Utilities ===
VALID_BITGET_SYMBOLS = set()

def load_valid_bitget_symbols():
    global VALID_BITGET_SYMBOLS
    try:
        url = "https://api.bitget.com/api/mix/v1/market/tickers?productType=umcbl"
        res = requests.get(url, timeout=10)
        data = res.json()["data"]
        VALID_BITGET_SYMBOLS = {item["symbol"].replace("_UMCBL", "") for item in data}
        logging.info(f"✅ Đã tải {len(VALID_BITGET_SYMBOLS)} coin từ Bitget.")
    except Exception as e:
        logging.error(f"❌ Không thể tải danh sách coin Bitget: {e}")

def get_bitget_price(symbol):
    try:
        symbol = symbol.upper()
        if symbol not in VALID_BITGET_SYMBOLS:
            logging.warning(f"⚠️ {symbol} không tồn tại trên Bitget.")
            return None
        url = f"https://api.bitget.com/api/mix/v1/market/ticker?symbol={symbol}_UMCBL"
        res = requests.get(url, timeout=5)
        if res.status_code != 200:
            raise Exception("Bitget trả lỗi")
        data = res.json()
        return float(data["data"]["last"])
    except Exception as e:
        logging.error(f"❌ Lỗi lấy giá từ Bitget ({symbol}): {e}")
        return None

# === Lấy dữ liệu lịch sử từ Binance ===
def fetch_price_data(symbol, interval="15m", limit=100):
    try:
        url = f"https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        df = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "num_trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        return df
    except Exception as e:
        logging.error(f"❌ Lỗi lấy dữ liệu lịch sử Binance: {symbol} – {e}")
        return None

# === Chỉ báo kỹ thuật ===
def calculate_williams_r(df, period=14):
    df = df.copy()
    df['wr'] = -100 * ((df['high'].rolling(period).max() - df['close']) /
                       (df['high'].rolling(period).max() - df['low'].rolling(period).min()))
    return df

def calculate_atr(df, period=14):
    df = df.copy()
    high = df['high']
    low = df['low']
    close = df['close']
    df['tr'] = pd.concat([
        high - low,
        abs(high - close.shift()),
        abs(low - close.shift())
    ], axis=1).max(axis=1)
    df['atr'] = df['tr'].rolling(period).mean()
    return df

# === Sinh tín hiệu BUY/SELL theo %R + ATR ===
def generate_signal(df):
    last = df.iloc[-1]
    wr = last['wr']
    atr = last['atr']
    close = last['close']

    if pd.isna(wr) or pd.isna(atr):
        return None

    signal = None
    if wr < -98:
        signal = "BUY"
    elif wr > -2:
        signal = "SELL"
    else:
        return None

    tp1 = round(close + atr * (1 if signal == "BUY" else -1), 4)
    tp2 = round(close + atr * 2 * (1 if signal == "BUY" else -1), 4)
    sl = round(close - atr * (1 if signal == "BUY" else -1), 4)

    logging.info(f"📈 Tín hiệu {signal} | WR={wr:.2f} | Entry={close:.4f}")
    return {
        "wr": round(wr, 2),
        "signal": signal,
        "entry": round(close, 4),
        "tp1": tp1,
        "tp2": tp2,
        "sl": sl
    }

# === Biểu đồ HTML (tuỳ chọn) ===
def plot_signal_chart(df, signal_info, symbol):
    import plotly.graph_objs as go
    trace = go.Scatter(x=df["timestamp"], y=df["close"], mode="lines", name="Close")
    layout = go.Layout(title=f"{symbol} - {signal_info['signal']}")
    fig = go.Figure(data=[trace], layout=layout)
    path = f"static/{symbol}.html"
    fig.write_html(path)
    logging.info(f"🖼️ Đã lưu biểu đồ {symbol} tại {path}")
    return path
