import os, pytz, datetime as dt, json
import yfinance as yf
import requests
from pathlib import Path

TZ = pytz.timezone(os.getenv("TZ", "America/New_York"))
FINNHUB = os.getenv("FINNHUB_API_KEY")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _read_json(fname: str) -> list[str]:
    try:
        with open(DATA_DIR / fname, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def load_universe() -> list[str]:
    """Return combined S&P500 + NDX100 ticker universe (deduped)."""
    spx = _read_json("sp500.json")
    ndx = _read_json("ndx100.json")
    tickers = sorted(set(spx + ndx))
    return [t for t in tickers if "^" not in t and "." not in t]


def _is_liquid(ticker: str) -> bool:
    """Basic liquidity screen: price >= $5 and avg volume >= 500k."""
    try:
        info = yf.Ticker(ticker).fast_info
        price = info.get("last_price") or info.get("previous_close") or 0
        avgvol = info.get("ten_day_average_volume") or info.get("last_volume") or 0
        return (price or 0) >= 5 and (avgvol or 0) >= 500_000
    except Exception:
        return False


def _pct(a: float, b: float):
    try:
        return round((a - b) / b * 100, 2)
    except Exception:
        return None


def _fetch_company_news(ticker: str, since_hours: int = 36):
    if not FINNHUB:
        return []
    to_ts = int(dt.datetime.now(tz=TZ).timestamp())
    from_ts = to_ts - since_hours * 3600
    url = (
        "https://finnhub.io/api/v1/company-news?"
        f"symbol={ticker}&from={dt.datetime.fromtimestamp(from_ts, TZ).date()}"
        f"&to={dt.datetime.fromtimestamp(to_ts, TZ).date()}&token={FINNHUB}"
    )
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()[:10]
    except Exception:
        return []


def _pick_reason(news: list[dict]):
    KEYS = [
        "earnings",
        "guidance",
        "forecast",
        "acquire",
        "acquisition",
        "merger",
        "M&A",
        "upgrade",
        "downgrade",
        "initiates",
        "FDA",
        "approval",
        "tariff",
        "contract",
        "lawsuit",
        "recall",
    ]
    for n in news:
        title = (n.get("headline") or n.get("title") or "").strip()
        if any(k.lower() in title.lower() for k in KEYS):
            return title, n.get("url")
    if news:
        return (news[0].get("headline") or news[0].get("title") or ""), news[0].get("url")
    return "", None


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------


def top_ah_moves(tickers: list[str], max_n: int = 6):
    """Return list[dict] of top after-hours moves (mix winners/losers)."""
    now = dt.datetime.now(TZ)
    y = now - dt.timedelta(days=1)
    start = TZ.localize(dt.datetime(y.year, y.month, y.day, 16, 0))
    end = TZ.localize(dt.datetime(y.year, y.month, y.day, 20, 0))
    winners, losers = [], []
    for t in tickers:
        if not _is_liquid(t):
            continue
        try:
            df = yf.download(
                t,
                start=start - dt.timedelta(minutes=5),
                end=end,
                interval="1m",
                prepost=True,
                progress=False,
            )
            if df.empty:
                continue
            first, last = float(df["Close"].iloc[0]), float(df["Close"].iloc[-1])
            pc = _pct(last, first)
            if pc is None or abs(pc) < 2:
                continue
            news = _fetch_company_news(t, since_hours=36)
            why, link = _pick_reason(news)
            item = {
                "ticker": t,
                "move": f"{pc:+}% AH",
                "why": (why[:140] + "…") if len(why) > 140 else why,
                "source_url": link,
            }
            (winners if pc > 0 else losers).append((abs(pc), item))
        except Exception:
            continue
    winners.sort(reverse=True)
    losers.sort(reverse=True)
    combined = winners[: max_n // 2] + losers[: max_n // 2]
    return [x[1] for x in combined]


def top_premarket_moves(tickers: list[str], max_n: int = 8):
    now = dt.datetime.now(TZ)
    start = TZ.localize(dt.datetime(now.year, now.month, now.day, 4, 0))
    end = TZ.localize(dt.datetime(now.year, now.month, now.day, 9, 10))
    winners, losers = [], []
    for t in tickers:
        if not _is_liquid(t):
            continue
        try:
            df = yf.download(
                t,
                start=start,
                end=end,
                interval="1m",
                prepost=True,
                progress=False,
            )
            if df.empty:
                continue
            first, last = float(df["Close"].iloc[0]), float(df["Close"].iloc[-1])
            vol = float(df["Volume"].sum())
            if vol < 80_000:
                continue
            pc = _pct(last, first)
            if pc is None or abs(pc) < 2:
                continue
            news = _fetch_company_news(t, since_hours=24)
            why, link = _pick_reason(news)
            item = {
                "ticker": t,
                "move": f"{pc:+}% pre",
                "why": (why[:140] + "…") if len(why) > 140 else why,
                "source_url": link,
            }
            (winners if pc > 0 else losers).append((abs(pc), item))
        except Exception:
            continue
    winners.sort(reverse=True)
    losers.sort(reverse=True)
    combined = winners[: max_n // 2] + losers[: max_n // 2]
    return [x[1] for x in combined]
