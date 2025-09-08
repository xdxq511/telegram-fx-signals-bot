import os
import time
import requests
import pandas as pd

ALPHA_URL = "https://www.alphavantage.co/query"

def fetch_fx(symbol: str, interval: str = "5min", max_retries: int = 3) -> pd.DataFrame:
    """Fetch intraday FX data for pairs like 'EURUSD' or 'XAUUSD' (use 'XAUUSD' via CURRENCY_EXCHANGE_RATE?).
    For standard FX, we use FX_INTRADAY. For metals like XAUUSD/XAGUSD, AlphaVantage doesn't offer intraday free tier;
    you can still test with common pairs (EURUSD, GBPUSD, USDJPY, etc.).
    """
    api_key = os.getenv("ALPHAVANTAGE_API_KEY", "")
    if not api_key:
        raise RuntimeError("Missing ALPHAVANTAGE_API_KEY")

    from_symbol = symbol[:3]
    to_symbol = symbol[3:]

    params = {
        "function": "FX_INTRADAY",
        "from_symbol": from_symbol,
        "to_symbol": to_symbol,
        "interval": interval,
        "outputsize": "compact",
        "apikey": api_key,
    }
    last_err = None
    for _ in range(max_retries):
        try:
            r = requests.get(ALPHA_URL, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            key = f"Time Series FX ({interval})"
            if key not in data:
                # API limit hit or error
                last_err = RuntimeError(str(data)[:200])
                time.sleep(15)
                continue
            df = pd.DataFrame.from_dict(data[key], orient="index").rename(
                columns={
                    "1. open": "open",
                    "2. high": "high",
                    "3. low": "low",
                    "4. close": "close",
                }
            )
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            df = df.astype(float)
            return df
        except Exception as e:
            last_err = e
            time.sleep(5)
    raise last_err if last_err else RuntimeError("Unknown fetch error")
