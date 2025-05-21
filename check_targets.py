import time
import logging
from signal_utils import (
    load_valid_bitget_symbols, fetch_price_data,
    calculate_williams_r, calculate_atr,
    generate_signal, send_telegram_message, log_open_signal
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

load_valid_bitget_symbols()

def load_coin_list():
    with open("coin_list.txt", "r") as f:
        return [line.strip().upper() for line in f if line.strip()]

def auto_check_signals():
    logging.info("🚀 Bắt đầu kiểm tra tín hiệu")
    for symbol in load_coin_list():
        try:
            df = fetch_price_data(symbol)
            if df is None or df.empty:
                continue
            df = calculate_williams_r(df)
            df = calculate_atr(df)
            signal_info = generate_signal(df)
            if signal_info:
                msg = (
                    f"<b>{symbol}</b> - {signal_info['signal']}\n"
                    f"WR: {signal_info['wr']} | Entry: {signal_info['entry']}\n"
                    f"TP1: {signal_info['tp1']} | TP2: {signal_info['tp2']} | SL: {signal_info['sl']}"
                )
                send_telegram_message(msg)
                log_open_signal(symbol, signal_info)
                logging.info(f"📈 {symbol} - {signal_info['signal']} đã gửi Telegram")
        except Exception as e:
            logging.error(f"❌ Lỗi khi xử lý {symbol}: {e}")

if __name__ == '__main__':
    while True:
        auto_check_signals()
        time.sleep(60)