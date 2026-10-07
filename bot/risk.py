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


def whole_shares(budget, price):
    return int(budget // price) if price > 0 else 0


def exit_reason(plpc, stop_pct, target_pct, held_days, max_hold_days, close_requested,
                days_to_expiry=None, min_days_to_expiry=2):
    """Why a position should be closed now, or None to keep it."""
    if plpc <= -stop_pct:
        return f"stop loss ({plpc:.1%})"
    if plpc >= target_pct:
        return f"profit target ({plpc:.1%})"
    if close_requested:
        return "Claude asked to close"
    if held_days >= max_hold_days:
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
