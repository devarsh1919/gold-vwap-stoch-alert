"""
GOLD XAUUSD — VWAP + Stochastic Alert System — Main Runner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Data:       Twelve Data WebSocket (free) — live tick feed
Candles:    Built in-process from ticks (5-minute default)
Indicators: Session VWAP + Stochastic Oscillator (12,3,3)
Strategy:   Price vs VWAP + Stochastic zone entry
Alerts:     Telegram Bot → your phone
Cloud:      Runs 24/7 on Render.com / Railway (free tier) so
            alerts keep firing even when your computer is off
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import os
import time
import json
import logging
import websocket
from datetime import datetime, timezone, timedelta

from candle_engine import CandleEngine
from strategy_vwap_stoch import VWAPStochasticStrategy
from telegram_bot import TelegramBot

# ─────────────────────────────────────────────
# CONFIG — Set these in Render/Railway environment vars
# ─────────────────────────────────────────────
TWELVE_DATA_KEY  = os.getenv("TWELVE_DATA_KEY",  "YOUR_API_KEY_HERE")
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN",   "YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

TIMEFRAME_MINUTES = int(os.getenv("TIMEFRAME_MINUTES", "5"))
STOCH_K_LENGTH     = int(os.getenv("STOCH_K_LENGTH", "12"))
STOCH_K_SMOOTH     = int(os.getenv("STOCH_K_SMOOTH", "3"))
STOCH_D_SMOOTH     = int(os.getenv("STOCH_D_SMOOTH", "3"))
STOCH_LOWER_BAND   = int(os.getenv("STOCH_LOWER_BAND", "20"))
STOCH_UPPER_BAND   = int(os.getenv("STOCH_UPPER_BAND", "80"))
VWAP_RESET_HOUR_UTC = int(os.getenv("VWAP_RESET_HOUR_UTC", "0"))   # 0 = midnight UTC, 22 = 22:00 UTC

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────
engine   = CandleEngine(timeframe_minutes=TIMEFRAME_MINUTES)
strategy = VWAPStochasticStrategy(
    k_length=STOCH_K_LENGTH,
    k_smooth=STOCH_K_SMOOTH,
    d_smooth=STOCH_D_SMOOTH,
    lower_band=STOCH_LOWER_BAND,
    upper_band=STOCH_UPPER_BAND,
)
telegram = TelegramBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

last_heartbeat     = time.time()
last_session_date  = None
session_start_idx  = 0


def check_new_session(candle_start_time: datetime):
    """
    Reset VWAP session at VWAP_RESET_HOUR_UTC (default 0 = midnight UTC).
    Trick: shift the timestamp back by the reset hour before taking the
    date — that makes the "session date" flip at the reset hour instead
    of at midnight.
    """
    global last_session_date, session_start_idx

    shifted = candle_start_time - timedelta(hours=VWAP_RESET_HOUR_UTC)
    current_date = shifted.date()
    if last_session_date != current_date:
        logger.info(f"🌅 New session: {current_date} UTC — Resetting VWAP")
        last_session_date = current_date
        # The candle that just closed is the first candle of the new session
        session_start_idx = len(engine.candles) - 1


def on_new_candle(candle):
    """Called every time a new 5-min candle closes — evaluate the strategy."""
    logger.info(f"🕯️  New candle: {candle}")

    check_new_session(candle.start_time)

    signal = strategy.check(engine, session_start_idx)
    if signal:
        logger.info(f"🚨 SIGNAL: {signal.signal_type} @ ${signal.price:.3f}")
        telegram.send(signal.message)


def on_message(ws, message):
    """Handle incoming WebSocket price tick from Twelve Data"""
    global last_heartbeat

    try:
        data = json.loads(message)

        if data.get("event") != "price":
            return

        price = float(data["price"])
        ts    = datetime.fromtimestamp(data["timestamp"], tz=timezone.utc)

        closed_candle = engine.process_tick(price, ts)
        if closed_candle:
            on_new_candle(closed_candle)

        # Hourly heartbeat so you know it's alive
        if time.time() - last_heartbeat > 3600:
            telegram.send_heartbeat(price, len(engine.candles))
            last_heartbeat = time.time()

    except Exception as e:
        logger.error(f"on_message error: {e}")


def on_error(ws, error):
    logger.error(f"WebSocket error: {error}")


def on_close(ws, close_status_code, close_msg):
    logger.warning(f"WebSocket closed: {close_status_code} — {close_msg}")
    logger.info("Reconnecting in 5 seconds...")
    time.sleep(5)
    start_websocket()


def on_open(ws):
    logger.info("✅ WebSocket connected to Twelve Data")
    subscribe = {
        "action": "subscribe",
        "params": {
            "symbols": "XAU/USD"
        }
    }
    ws.send(json.dumps(subscribe))


def start_websocket():
    """Start Twelve Data WebSocket connection"""
    url = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={TWELVE_DATA_KEY}"
    ws = websocket.WebSocketApp(
        url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever(ping_interval=30, ping_timeout=10)


def main():
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("  GOLD XAUUSD VWAP + Stochastic Alert System v1.0")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info(f"  Timeframe  : {TIMEFRAME_MINUTES}-min candles")
    logger.info(f"  Stochastic : ({STOCH_K_LENGTH},{STOCH_K_SMOOTH},{STOCH_D_SMOOTH})")
    logger.info(f"  Zones      : Buy <= {STOCH_LOWER_BAND} | Sell >= {STOCH_UPPER_BAND}")
    logger.info(f"  VWAP Reset : {VWAP_RESET_HOUR_UTC}:00 UTC")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    telegram.send_startup(
        TIMEFRAME_MINUTES, STOCH_K_LENGTH, STOCH_K_SMOOTH,
        STOCH_D_SMOOTH, STOCH_LOWER_BAND, STOCH_UPPER_BAND,
        VWAP_RESET_HOUR_UTC
    )

    start_websocket()


if __name__ == "__main__":
    main()