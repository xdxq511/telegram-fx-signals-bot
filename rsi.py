import pandas as pd
from ta.momentum import RSIIndicator

def rsi_signals(df: pd.DataFrame, low: float = 30, high: float = 70, window: int = 14):
    """Return last signal string or None based on RSI cross events."""
    close = df['close']
    rsi = RSIIndicator(close, window=window).rsi()
    df = df.copy()
    df['rsi'] = rsi
    # Consider last two bars to detect cross
    if len(df) < 2:
        return None

    prev = df.iloc[-2]
    last = df.iloc[-1]

    # Cross up from below 'low'
    if prev['rsi'] <= low and last['rsi'] > low:
        return f"RSI cross-up from {prev['rsi']:.1f} to {last['rsi']:.1f} → Potential BUY"
    # Cross down from above 'high'
    if prev['rsi'] >= high and last['rsi'] < high:
        return f"RSI cross-down from {prev['rsi']:.1f} to {last['rsi']:.1f} → Potential SELL"
    # Optional: oversold/overbought alerts
    if last['rsi'] < low:
        return f"RSI {last['rsi']:.1f} (oversold) → Watch for BUY setup"
    if last['rsi'] > high:
        return f"RSI {last['rsi']:.1f} (overbought) → Watch for SELL setup"
    return None
