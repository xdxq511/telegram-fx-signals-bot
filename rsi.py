import pandas as pd

def rsi_series(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's RSI using EWMA
    avg_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def rsi_signals(df: pd.DataFrame, low: float = 30, high: float = 70, window: int = 14):
    if 'close' not in df.columns or len(df) < window + 2:
        return None
    df = df.copy()
    df['rsi'] = rsi_series(df['close'], window=window)

    prev = df.iloc[-2]
    last = df.iloc[-1]

    if pd.notna(prev['rsi']) and pd.notna(last['rsi']):
        if prev['rsi'] <= low and last['rsi'] > low:
            return f"RSI cross-up من {prev['rsi']:.1f} إلى {last['rsi']:.1f} → احتمال BUY"
        if prev['rsi'] >= high and last['rsi'] < high:
            return f"RSI cross-down من {prev['rsi']:.1f} إلى {last['rsi']:.1f} → احتمال SELL"
        if last['rsi'] < low:
            return f"RSI {last['rsi']:.1f} (Oversold) → ترقّب BUY"
        if last['rsi'] > high:
            return f"RSI {last['rsi']:.1f} (Overbought) → ترقّب SELL"
    return None
