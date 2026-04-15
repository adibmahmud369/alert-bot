"""
Price Fetcher — Binance থেকে BTC/ETH/SOL, CoinGecko থেকে TOTAL3/USDT.D
"""

import logging
import ccxt
import requests

logger = logging.getLogger(__name__)
_exchange = ccxt.binance({"enableRateLimit": True})


def get_price(asset: str) -> float | None:
    try:
        if asset in ("BTC", "ETH", "SOL"):
            ticker = _exchange.fetch_ticker(f"{asset}/USDT")
            return float(ticker["last"])
        elif asset == "TOTAL3":
            return _get_total3()
        elif asset == "USDT.D":
            return _get_usdt_dominance()
    except Exception as e:
        logger.warning(f"Price fetch error [{asset}]: {e}")
    return None


def _get_total3() -> float | None:
    r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
    r.raise_for_status()
    d = r.json()["data"]
    total = d["total_market_cap"]["usd"]
    btc = d["market_cap_percentage"].get("btc", 0) / 100
    eth = d["market_cap_percentage"].get("eth", 0) / 100
    return round(total * (1 - btc - eth) / 1e9, 2)  # Billions এ


def _get_usdt_dominance() -> float | None:
    r = requests.get("https://api.coingecko.com/api/v3/global", timeout=10)
    r.raise_for_status()
    return round(r.json()["data"]["market_cap_percentage"].get("usdt", 0), 4)