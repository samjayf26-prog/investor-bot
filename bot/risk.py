"""Risk limits as pure functions. Each returns (ok, reason) or a number; no I/O."""
import math

RISK_DIAL = {"normal": 1.0, "reduced": 0.5, "off": 0.0}


def dial_multiplier(dial):
    """Unknown dial values count as 'off': garbage can only make the bot trade less."""
    return RISK_DIAL.get(dial, 0.0)


def symbol_allowed(symbol, universe):
    if symbol not in universe:
        return False, f"{symbol} is not in the universe {universe}"
    return True, ""


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


def position_notional(equity, cash, max_frac, multiplier, max_notional, min_notional):
    """Dollar size of the entry: never more than max_frac of equity, the cash on hand
    (no leverage), or the hard ceiling. Returns 0.0 when below the broker minimum."""
    if equity <= 0 or cash <= 0:
        return 0.0
    size = min(equity * max_frac * min(max(multiplier, 0.0), 1.0), cash * 0.98, max_notional)
    size = math.floor(size * 100) / 100
    return size if size >= min_notional else 0.0


def stop_hit(unrealized_plpc, stop_pct):
    """unrealized_plpc is the position's return as a fraction (Alpaca's field)."""
    return unrealized_plpc <= -stop_pct


def entry_signal(prev_close, price_at_10, threshold, long_only):
    """Intraday momentum: the move from yesterday's close to 10:00 ET picks the direction
    for the last half hour. Returns 'long', 'short' or None."""
    if not prev_close or not price_at_10 or prev_close <= 0:
        return None
    r1 = price_at_10 / prev_close - 1
    if r1 > threshold:
        return "long"
    if r1 < -threshold and not long_only:
        return "short"
    return None
