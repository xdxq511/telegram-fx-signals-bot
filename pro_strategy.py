# pro_strategy.py
import pandas as pd

# ==== مؤشرات بسيطة بدون مكتبات خارجية ====
def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def rsi_series(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def macd_series(close: pd.Series, fast=12, slow=26, signal=9):
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist

def atr_series(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/n, adjust=False, min_periods=n).mean()
    return atr

# ==== إشارة البرو ====
def pro_signal_for_pair(df: pd.DataFrame,
                        rsi_low=25, rsi_high=75,
                        atr_mult=1.5, rr_ratio=2.0):
    """
    يرجّع dict فيها تفاصيل الصفقة المقترحة إذا توفرت شروط برو، وإلا None.
    الشروط:
      BUY: RSI<25 + MACD cross up + close > EMA200
      SELL: RSI>75 + MACD cross down + close < EMA200
    SL من ATR*1.5، و TP بنسبة RR_ratio.
    """
    needed = {"open","high","low","close"}
    if not needed.issubset(set(df.columns)) or len(df) < 210:
        return None

    df = df.copy()
    close = df["close"]
    high, low = df["high"], df["low"]

    df["ema200"] = ema(close, 200)
    df["rsi"] = rsi_series(close, 14)
    macd_line, signal_line, hist = macd_series(close)
    df["macd"], df["macd_signal"], df["macd_hist"] = macd_line, signal_line, hist
    df["atr"] = atr_series(high, low, close, 14)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if pd.isna(last[["ema200","rsi","macd_hist","atr"]]).any() or pd.isna(prev["macd_hist"]):
        return None

    entry = float(last["close"])
    ema200 = float(last["ema200"])
    atr_val = float(last["atr"])
    rsi_val = float(last["rsi"])
    macd_cross_up   = (prev["macd_hist"] <= 0) and (last["macd_hist"] > 0)
    macd_cross_down = (prev["macd_hist"] >= 0) and (last["macd_hist"] < 0)

    direction = None
    if (rsi_val < rsi_low) and macd_cross_up and (entry > ema200):
        direction = "BUY"
        sl = entry - atr_mult * atr_val
        tp = entry + rr_ratio * (entry - sl)
    elif (rsi_val > rsi_high) and macd_cross_down and (entry < ema200):
        direction = "SELL"
        sl = entry + atr_mult * atr_val
        tp = entry - rr_ratio * (sl - entry)
    else:
        return None

    rr = abs((tp - entry) / (entry - sl)) if (entry - sl) != 0 else None

    return {
        "direction": direction,
        "entry": round(entry, 5),
        "sl": round(sl, 5),
        "tp": round(tp, 5),
        "rsi": round(rsi_val, 2),
        "ema200": round(ema200, 5),
        "atr": round(atr_val, 5),
        "rr": round(rr, 2) if rr is not None else None,
        "macd_hist_prev": round(float(prev["macd_hist"]), 5),
        "macd_hist": round(float(last["macd_hist"]), 5),
    }
