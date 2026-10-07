"""Thin Alpaca REST client (trading + market data), standard library only."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

PAPER_URL = "https://paper-api.alpaca.markets"
LIVE_URL = "https://api.alpaca.markets"
DATA_URL = "https://data.alpaca.markets"


class AlpacaError(Exception):
    def __init__(self, status, body):
        super().__init__(f"Alpaca HTTP {status}: {body}")
        self.status = status


class Alpaca:
    def __init__(self, key_id, secret, live):
        self.base = LIVE_URL if live else PAPER_URL
        self.headers = {
            "APCA-API-KEY-ID": key_id,
            "APCA-API-SECRET-KEY": secret,
            "Content-Type": "application/json",
        }

    @classmethod
    def from_env(cls, live):
        prefix = "ALPACA_LIVE" if live else "ALPACA_PAPER"
        key, secret = os.environ.get(f"{prefix}_KEY_ID"), os.environ.get(f"{prefix}_SECRET")
        if not key or not secret:
            raise SystemExit(f"Missing {prefix}_KEY_ID / {prefix}_SECRET secrets")
        return cls(key, secret, live)

    def _req(self, method, url, params=None, body=None, retries=3):
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(retries):
            req = urllib.request.Request(url, data=data, method=method, headers=self.headers)
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    raw = r.read()
                    return json.loads(raw) if raw else None
            except urllib.error.HTTPError as e:
                text = e.read().decode(errors="replace")
                # Retry only server errors and rate limits; 4xx means the request is wrong.
                if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                    time.sleep(2 ** attempt * 2)
                    continue
                raise AlpacaError(e.code, text) from None
            except urllib.error.URLError:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt * 2)
                    continue
                raise

    # trading
    def clock(self):
        return self._req("GET", f"{self.base}/v2/clock")

    def calendar(self, start, end):
        return self._req("GET", f"{self.base}/v2/calendar", {"start": start, "end": end})

    def account(self):
        return self._req("GET", f"{self.base}/v2/account")

    def positions(self):
        return self._req("GET", f"{self.base}/v2/positions")

    def portfolio_history(self):
        return self._req("GET", f"{self.base}/v2/account/portfolio/history",
                         {"period": "1A", "timeframe": "1D"})

    def order_by_client_id(self, client_order_id):
        try:
            return self._req("GET", f"{self.base}/v2/orders:by_client_order_id",
                             {"client_order_id": client_order_id})
        except AlpacaError as e:
            if e.status == 404:
                return None
            raise

    def submit_order(self, **order):
        return self._req("POST", f"{self.base}/v2/orders", body=order, retries=1)

    def cancel_all_orders(self):
        return self._req("DELETE", f"{self.base}/v2/orders")

    def close_position(self, symbol):
        return self._req("DELETE", f"{self.base}/v2/positions/{symbol}", retries=1)

    # market data
    def bars(self, symbol, timeframe, start, end):
        out = self._req("GET", f"{DATA_URL}/v2/stocks/{symbol}/bars",
                        {"timeframe": timeframe, "start": start, "end": end,
                         "feed": "sip", "adjustment": "raw", "limit": 1000})
        return out.get("bars") or []
