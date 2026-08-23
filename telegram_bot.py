"""
Telegram Alert Bot
Sends formatted trade signals to your phone instantly
"""

import requests
import logging

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self.token   = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"

    def send(self, message: str) -> bool:
        """Send a message to Telegram. Returns True if successful."""
        try:
            url  = f"{self.base_url}/sendMessage"
            data = {
                "chat_id":    self.chat_id,
                "text":       message,
                "parse_mode": "Markdown"
            }
            resp = requests.post(url, data=data, timeout=10)
            if resp.status_code == 200:
                logger.info(f"✅ Telegram alert sent: {message[:60]}...")
                return True
            else:
                logger.error(f"❌ Telegram error {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Telegram exception: {e}")
            return False

    def send_startup(self, timeframe_minutes: int, k_length: int, k_smooth: int,
                      d_smooth: int, lower_band: int, upper_band: int,
                      vwap_reset_hour_utc: int = 0):
        """Send system startup notification"""
        msg = (
            f"🚀 *GOLD VWAP + Stochastic Alert System Started*\n"
            f"Symbol: XAUUSD\n"
            f"Timeframe: {timeframe_minutes}-minute candles\n"
            f"Stochastic: ({k_length}, {k_smooth}, {d_smooth})\n"
            f"Zones: Buy ≤ {lower_band} | Sell ≥ {upper_band}\n"
            f"VWAP Reset: {vwap_reset_hour_utc}:00 UTC\n"
            f"━━━━━━━━━━━━━━\n"
            f"BUY  → price above VWAP + Stoch enters {lower_band} zone\n"
            f"SELL → price below VWAP + Stoch enters {upper_band} zone\n"
            f"━━━━━━━━━━━━━━\n"
            f"System is live and monitoring!"
        )
        self.send(msg)

    def send_heartbeat(self, price: float, candle_count: int):
        """Optional: send hourly heartbeat so you know system is alive"""
        msg = (
            f"💓 *System Heartbeat*\n"
            f"XAUUSD: ${price:.3f}\n"
            f"Candles formed: {candle_count}\n"
            f"System: Running ✅"
        )
        self.send(msg)