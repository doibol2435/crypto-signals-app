from flask import Flask, render_template, jsonify
from signal_utils import (
    fetch_price_data, calculate_williams_r, calculate_atr,
    generate_signal, send_telegram_message, plot_signal_chart,
    log_open_signal, get_bitget_price, load_valid_bitget_symbols
)
import os
import json
import requests
import logging
from datetime import datetime, timedelta

app = Flask(__name__)
load_valid_bitget_symbols()

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"⚠️ Exception: {str(e)}")
    send_telegram_message(f"🚨 Lỗi hệ thống: <code>{str(e)}</code>")
    return f"Lỗi: {str(e)}", 500

def delete_old_logs():
    try:
        if os.path.exists("signals.log"):
            mtime = datetime.fromtimestamp(os.path.getmtime("signals.log"))
            if datetime.now() - mtime > timedelta(days=7):
                os.remove("signals.log")
                logging.info("🗑️ Đã xoá file signals.log cũ quá 7 ngày.")
    except Exception as e:
        logging.error(f"❌ Lỗi khi xoá log: {e}")
        send_telegram_message(f"🚨 Lỗi xoá log: <code>{str(e)}</code>")

delete_old_logs()

@app.route('/')
def index():
    return "Crypto Signals App is running"

@app.route('/logs')
def view_logs():
    try:
        with open("signals.log", "r", encoding="utf-8") as f:
            return f"<pre>{f.read()[-4000:]}</pre>"
    except:
        return "Không thể đọc signals.log"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)