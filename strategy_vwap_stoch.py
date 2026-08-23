"""
Strategy: VWAP + Stochastic Oscillator (12, 3, 3)
XAUUSD Gold Alert System

RULES (as specified):
  BUY alert  -> Price is ABOVE session VWAP  AND  Stochastic %K drops into
                the lower band (<= 20)
  SELL alert -> Price is BELOW session VWAP  AND  Stochastic %K rises into
                the upper band (>= 80)

Alerts are edge-triggered: you get ONE alert when %K first enters the zone,
not one every candle while it sits there. The zone "re-arms" once %K leaves
it, so the next time price dips into 20 (or spikes into 80) again, you get
a fresh alert.
"""

from dataclasses import dataclass
from typing import Optional
from indicators import calc_stochastic, calc_session_vwap


@dataclass
class Signal:
    strategy_name: str
    signal_type: str          # "BUY" or "SELL"
    price: float
    vwap: float
    stoch_k: float
    stoch_d: float
    message: str


class VWAPStochasticStrategy:
    def __init__(self, k_length=12, k_smooth=3, d_smooth=3,
                 lower_band=20, upper_band=80):
        self.k_length   = k_length
        self.k_smooth   = k_smooth
        self.d_smooth   = d_smooth
        self.lower_band = lower_band
        self.upper_band = upper_band

        # Zone-armed flags so we only alert once per dip/spike, not every candle
        self.buy_zone_armed  = True   # ready to fire a BUY alert
        self.sell_zone_armed = True   # ready to fire a SELL alert

    def check(self, engine, session_start_idx: int) -> Optional[Signal]:
        opens  = engine.get_opens()
        closes = engine.get_closes()
        highs  = engine.get_highs()
        lows   = engine.get_lows()
        volumes = engine.get_ticks()

        if len(closes) < self.k_length + self.d_smooth:
            return None

        k_line, d_line = calc_stochastic(
            closes, highs, lows, self.k_length, self.k_smooth, self.d_smooth
        )
        vwap_line = calc_session_vwap(opens, highs, lows, closes, volumes, session_start_idx)

        k1, k0 = k_line[-1], k_line[-2]
        vwap1 = vwap_line[-1]
        d1 = d_line[-1]

        if k1 is None or k0 is None or vwap1 is None:
            return None

        price = closes[-1]
        above_vwap = price > vwap1
        below_vwap = price < vwap1

        # ── Re-arm zones once %K exits them ──
        if k1 > self.lower_band:
            self.buy_zone_armed = True
        if k1 < self.upper_band:
            self.sell_zone_armed = True

        # ── BUY: price above VWAP + %K just dropped into oversold zone ──
        entered_lower = k0 >= self.lower_band and k1 < self.lower_band
        if above_vwap and entered_lower and self.buy_zone_armed:
            self.buy_zone_armed = False
            return Signal(
                strategy_name="VWAP + Stochastic",
                signal_type="BUY",
                price=price,
                vwap=vwap1,
                stoch_k=k1,
                stoch_d=d1 if d1 is not None else 0.0,
                message=(
                    f"🟢 *GOLD BUY — VWAP + Stochastic*\n"
                    f"Price: ${price:.3f} (above VWAP ✅)\n"
                    f"VWAP: ${vwap1:.3f}\n"
                    f"Stoch %K: {k1:.1f} | %D: {(d1 or 0):.1f} — entered oversold (≤{self.lower_band}) ✅\n"
                    f"📌 Bullish pullback setup — price trending above VWAP, "
                    f"stochastic dipped into the buy zone."
                )
            )

        # ── SELL: price below VWAP + %K just rose into overbought zone ──
        entered_upper = k0 <= self.upper_band and k1 > self.upper_band
        if below_vwap and entered_upper and self.sell_zone_armed:
            self.sell_zone_armed = False
            return Signal(
                strategy_name="VWAP + Stochastic",
                signal_type="SELL",
                price=price,
                vwap=vwap1,
                stoch_k=k1,
                stoch_d=d1 if d1 is not None else 0.0,
                message=(
                    f"🔴 *GOLD SELL — VWAP + Stochastic*\n"
                    f"Price: ${price:.3f} (below VWAP ✅)\n"
                    f"VWAP: ${vwap1:.3f}\n"
                    f"Stoch %K: {k1:.1f} | %D: {(d1 or 0):.1f} — entered overbought (≥{self.upper_band}) ✅\n"
                    f"📌 Bearish pullback setup — price trending below VWAP, "
                    f"stochastic spiked into the sell zone."
                )
            )

        return None
