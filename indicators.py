"""
Indicator Library — Stochastic Oscillator + Session VWAP
Used by the VWAP + Stochastic Gold Alert System
"""


def calc_stochastic(closes, highs, lows, k_length=12, k_smooth=3, d_smooth=3):
    """
    Stochastic Oscillator.
    %K raw   = 100 * (close - lowest_low(k_length)) / (highest_high(k_length) - lowest_low(k_length))
    %K       = SMA(%K raw, k_smooth)   <- this is the "Stochastic" line most platforms plot
    %D       = SMA(%K, d_smooth)       <- the signal line
    Returns (k_line, d_line) as lists the same length as `closes`, with None
    for indices where there isn't enough history yet.
    """
    n = len(closes)
    raw_k = [None] * n

    for i in range(n):
        if i < k_length - 1:
            continue
        window_high = max(highs[i - k_length + 1:i + 1])
        window_low  = min(lows[i - k_length + 1:i + 1])
        if window_high == window_low:
            raw_k[i] = 50.0
        else:
            raw_k[i] = 100 * (closes[i] - window_low) / (window_high - window_low)

    def sma_skip_none(values, period):
        out = [None] * len(values)
        for i in range(len(values)):
            if values[i] is None:
                continue
            window = [v for v in values[max(0, i - period + 1):i + 1] if v is not None]
            if len(window) < period:
                continue
            out[i] = sum(window) / period
        return out

    k_line = sma_skip_none(raw_k, k_smooth)
    d_line = sma_skip_none(k_line, d_smooth)
    return k_line, d_line


def calc_session_vwap(opens, highs, lows, closes, volumes, session_start_idx: int):
    """
    Session VWAP, resetting at session_start_idx.
    Source = (Open + High + Low + Close) / 4, matching the TradingView VWAP
    indicator's "Source" setting used on the live chart.
    Returns a list the same length as `closes`, with None before the session starts.
    """
    n = len(closes)
    vwap_vals = [None] * n
    if session_start_idx >= n or session_start_idx < 0:
        return vwap_vals

    cum_tp_vol = 0.0
    cum_vol = 0.0

    for i in range(session_start_idx, n):
        tp = (opens[i] + highs[i] + lows[i] + closes[i]) / 4
        vol = volumes[i] if volumes[i] else 1.0
        cum_tp_vol += tp * vol
        cum_vol += vol
        vwap_vals[i] = cum_tp_vol / cum_vol

    return vwap_vals
