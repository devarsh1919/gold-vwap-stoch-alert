"""
Candle Engine — Builds real-time OHLC candles from a tick price feed.
Used instead of Renko for the VWAP + Stochastic strategy.
"""

from datetime import datetime, timezone


class Candle:
    def __init__(self, open_price, high, low, close, start_time, ticks=1):
        self.open  = open_price
        self.high  = high
        self.low   = low
        self.close = close
        self.start_time = start_time   # bucket start (UTC)
        self.ticks = ticks             # tick-count volume proxy

    def __repr__(self):
        return f"Candle({self.start_time} O:{self.open} H:{self.high} L:{self.low} C:{self.close})"


class CandleEngine:
    def __init__(self, timeframe_minutes: int = 5):
        self.timeframe_seconds = timeframe_minutes * 60
        self.candles: list[Candle] = []
        self._current: Candle | None = None
        self._current_bucket = None

    def _bucket_start(self, ts: datetime) -> datetime:
        """Floor a timestamp down to the start of its N-minute bucket (UTC)."""
        epoch = ts.timestamp()
        bucket_epoch = epoch - (epoch % self.timeframe_seconds)
        return datetime.fromtimestamp(bucket_epoch, tz=timezone.utc)

    def process_tick(self, price: float, ts: datetime) -> Candle | None:
        """
        Feed one price tick. Returns the CLOSED candle if this tick started
        a new bucket, otherwise returns None (current candle still forming).
        """
        bucket = self._bucket_start(ts)
        closed = None

        if self._current is None:
            self._current = Candle(price, price, price, price, bucket)
            self._current_bucket = bucket
            return None

        if bucket != self._current_bucket:
            # Finalize the previous candle
            closed = self._current
            self.candles.append(closed)
            # Start a new candle, opening at the previous close
            self._current = Candle(closed.close, price, price, price, bucket)
            self._current_bucket = bucket
        else:
            c = self._current
            c.high  = max(c.high, price)
            c.low   = min(c.low, price)
            c.close = price
            c.ticks += 1

        return closed

    def get_opens(self) -> list[float]:
        return [c.open for c in self.candles]

    def get_closes(self) -> list[float]:
        return [c.close for c in self.candles]

    def get_highs(self) -> list[float]:
        return [c.high for c in self.candles]

    def get_lows(self) -> list[float]:
        return [c.low for c in self.candles]

    def get_ticks(self) -> list[float]:
        return [c.ticks for c in self.candles]

    def last_candle(self) -> Candle | None:
        return self.candles[-1] if self.candles else None
