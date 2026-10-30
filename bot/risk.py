"""Risk limits and trade math as pure functions; no I/O."""
import math
from datetime import date

CONVICTION_FRAC = {1: 0.15, 2: 0.25, 3: 0.40}


def daily_loss_ok(equity, start_of_day_equity, cap_pct):
    """No new entries once today's loss reaches cap_pct of start-of-day equity."""
    if start_of_day_equity <= 0:
        return False, "start-of-day equity is not positive"
    loss = (start_of_day_equity - equity) / start_of_day_equity
    if loss >= cap_pct:
        return False, f"daily loss {loss:.2%} reached cap {cap_pct:.2%}"
    return True, ""


def drawdown_ok(equity, peak_equity, halt_pct):
    """Halt while equity is more than halt_pct below its peak. With no trades the peak
    is never regained, so the halt latches until Sam raises drawdown_halt_pct."""
    if peak_equity <= 0:
        return True, ""
    dd = (peak_equity - equity) / peak_equity
    if dd >= halt_pct:
        return False, f"drawdown {dd:.2%} from peak ${peak_equity:.2f} reached halt {halt_pct:.2%}"
    return True, ""


def pick_budget(equity, cash, conviction, max_notional, min_notional):
    """Dollars for one pick: a share of equity set by conviction, never more than the
    cash on hand (no leverage) or the hard ceiling. 0.0 when below the broker minimum."""
    if equity <= 0 or cash <= 0:
        return 0.0
    size = min(equity * CONVICTION_FRAC.get(conviction, 0.15), cash * 0.98, max_notional)
    size = math.floor(size * 100) / 100
    return size if size >= min_notional else 0.0


def sizing_view(equity, cash, positions_value, cap):
    """Size as if the account held at most `cap` dollars, so a big paper account trades
    like the real $100 one. Returns (equity, cash) to size with."""
    return min(equity, cap), max(0.0, min(cash, cap - positions_value))


def entry_limit(last_price, max_entry_price=None, slack=0.01):
    """Limit price for a stock entry: Claude's max entry price, or 1% over the last trade,
    whichever is lower. Rounded down to the cent."""
    cap = last_price * (1 + slack)
    if max_entry_price:
        cap = min(cap, max_entry_price)
    return math.floor(cap * 100) / 100


def whole_shares(budget, price):
    return int(budget // price) if price > 0 else 0


def exit_reason(plpc, stop_pct, target_pct, held_days, max_hold_days, close_requested,
                days_to_expiry=None, min_days_to_expiry=2, late_in_day=False):
    """Why a position should be closed now, or None to keep it.

    max_hold_days 0 is a day trade: held until late_in_day (15:30 ET), never overnight.
    target_pct None means no profit target: the time exit does the work."""
    if plpc <= -stop_pct:
        return f"stop loss ({plpc:.1%})"
    if target_pct is not None and plpc >= target_pct:
        return f"profit target ({plpc:.1%})"
    if close_requested:
        return "Claude asked to close"
    if max_hold_days == 0:
        if held_days >= 1 or late_in_day:
            return "day trade: end of day"
    elif held_days >= max_hold_days:
        return f"max hold of {max_hold_days} days"
    if days_to_expiry is not None and days_to_expiry <= min_days_to_expiry:
        return "option near expiry"
    return None


def choose_put(contracts, quotes, underlying_price, budget, today, min_days=10, max_days=45):
    """Pick the put closest to at-the-money whose ask fits the budget for one contract,
    expiring min_days..max_days out. Returns (contract, ask) or (None, None)."""
    best = None
    for c in contracts:
        if not c.get("tradable", True):
            continue
        days = (date.fromisoformat(c["expiration_date"]) - today).days
        q = quotes.get(c["symbol"]) or {}
        ask, bid = float(q.get("ap") or 0), float(q.get("bp") or 0)
        if not (min_days <= days <= max_days) or ask <= 0 or ask * 100 > budget:
            continue
        if bid <= 0 or (ask - bid) / ask > 0.35:  # skip illiquid contracts with huge spreads
            continue
        score = (abs(float(c["strike_price"]) - underlying_price), days)
        if best is None or score < best[0]:
            best = (score, c, ask)
    return (best[1], best[2]) if best else (None, None)


def vwap_confirms(last, vwap, bullish=True):
    """Entry confirmation: buy only while the price is on the right side of today's VWAP
    (above it for a stock buy, below it for a put). No VWAP means no confirmation."""
    if not last or not vwap:
        return False
    return last > vwap if bullish else last < vwap


def market_row(snap):
    """One symbol's line in state/market.json from an Alpaca snapshot, or None."""
    try:
        last = float(snap["latestTrade"]["p"])
    except (KeyError, TypeError, ValueError):
        return None
    day, prev = snap.get("dailyBar") or {}, snap.get("prevDailyBar") or {}

    def pct(base):
        try:
            return round((last / float(base) - 1) * 100, 2)
        except (TypeError, ValueError, ZeroDivisionError):
            return None

    vwap = day.get("vw")
    return {"last": last, "pct_vs_prev_close": pct(prev.get("c")), "pct_vs_open": pct(day.get("o")),
            "vwap": vwap, "vwap_side": None if not vwap else ("above" if last > vwap else "below")}


# leveraged core (review/profit-overhaul.md 3.1): signals as pure functions, closes oldest first
def sma_trend(closes, days=200):
    """1 when the last close is above the simple average of the last `days` closes (the
    last close included), else 0. Too little history counts as no trend (no leverage)."""
    if len(closes) < days:
        return 0
    return 1 if closes[-1] > sum(closes[-days:]) / days else 0


def realized_vol(closes, days=20):
    """Annualized sample standard deviation of the last `days` daily returns, or None."""
    if len(closes) < days + 1:
        return None
    rets = [closes[i] / closes[i - 1] - 1 for i in range(len(closes) - days, len(closes))]
    mean = sum(rets) / days
    var = sum((r - mean) ** 2 for r in rets) / (days - 1)
    return math.sqrt(var) * math.sqrt(252)


def core_weight(trend, vol, target=0.30, lev=3.0):
    """Share of the core in the 3x fund: lever it so that its own volatility is about
    `target`, never above 100%, and nothing while the index is below its trend."""
    if not trend or vol is None:
        return 0.0
    if vol <= 0:
        return 1.0
    return min(1.0, target / (lev * vol))


def dip_state(closes, prev_state, down_days=3, max_days=5):
    """Dip overlay: after `down_days` lower closes in a row the core goes all-in the 3x fund
    and stays until the first close above the one before, or `max_days` sessions.
    State is 0 (off) or the number of sessions the overlay will have been held after
    this close (1 on entry). Call once per session with that session's close last."""
    if prev_state > 0:
        if len(closes) >= 2 and closes[-1] > closes[-2]:
            return 0
        return 0 if prev_state >= max_days else prev_state + 1
    if len(closes) < down_days + 1:
        return 0
    tail = closes[-(down_days + 1):]
    return 1 if all(tail[i] < tail[i - 1] for i in range(1, len(tail))) else 0


def dip_replay(closes, down_days=3, max_days=5):
    """dip_state replayed over the whole series from a cold start: the overlay state after
    the last close, whatever earlier evaluations were missed (self-healing)."""
    state = 0
    for i in range(1, len(closes) + 1):
        state = dip_state(closes[max(0, i - down_days - 1):i], state, down_days, max_days)
    return state


def rebalance_needed(held_weight, target_weight, band=0.10):
    """Trade only when the target moved more than `band` from what is held, or when the
    3x sleeve switches between zero and something (same rule as the backtest's band)."""
    if target_weight == 0 and held_weight > 0:
        return True
    if held_weight == 0 and target_weight > 0:
        return True
    return abs(target_weight - held_weight) > band


def core_target(idle, weight, in_dip):
    """Dollars for (3x fund, rest) out of `idle` core dollars: the overlay means 100% 3x."""
    idle = max(0.0, idle)
    lev = idle if in_dip else idle * weight
    return round(float(lev), 2), round(float(idle - lev), 2)


def simulate_core(index_closes, lev_closes, rest_closes, start_value, sma_days=200, vol_days=20,
                  target=0.30, lev=3.0, band=0.10, down_days=3, max_days=5, start_at=None):
    """The core rule replayed on aligned daily closes (oldest first): returns the value
    path from `start_at` (index into the lists; default: the first day with signals).
    Weight over day t is set from closes through t-1; the overlay follows dip_state."""
    n = min(len(index_closes), len(lev_closes), len(rest_closes))
    first = max(sma_days, vol_days + 1, down_days + 1)
    if start_at is None:
        start_at = first
    values, held, dip, value = [], 0.0, 0, float(start_value)
    for t in range(first, n):
        hist = index_closes[:t]                       # through t-1
        w = core_weight(sma_trend(hist, sma_days), realized_vol(hist, vol_days), target, lev)
        dip = dip_state(hist, dip, down_days, max_days)
        want = 1.0 if dip else w
        if rebalance_needed(held, want, band):
            held = want
        if t >= start_at:
            r = held * (lev_closes[t] / lev_closes[t - 1] - 1) + (1 - held) * (rest_closes[t] / rest_closes[t - 1] - 1)
            value *= 1 + r
            values.append(value)
    return values
