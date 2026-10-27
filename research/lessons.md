# Lessons (rewritten by the evening review 2026-10-27; the morning research must follow these)

Evidence base: 6 closed paper picks (10-07 to 10-13, net +$0.89: PENG +2.07, UNH +0.42, SH +0.03, SOXS -0.11, HUM -0.32, CEG -0.74) and 8 closed live picks (MMM +$0.14 at its 7-day max hold, AZZ -$0.82, HAL -$0.55, SQQQ same-day -$0.25 and +$0.11, TQQQ same-day -$0.15, -$0.11 and +$0.12). Open: LMT (10-23, +6.3%), TSLA (10-26, +3.4%), CLS (10-27, flat) and the SPY core. Live account since 10-13: $73.94 (-1.41%) vs $74.22 in the S&P 500 (-1.04%), behind by $0.28. Tiny sample: treat as leanings, not laws.

Catalysts
- Prefer lasting estimate changes (guidance raise, rating reversal) over one-day headlines. PENG (+$2.07) is still the only real winner. A raise alone isn't enough: AZZ (beat and raise, ~3% gap) faded in two days for -$0.82 when small caps sold off on rates.
- Big names with fresh news are first-class candidates (PROMPT.md, review/megacap-results.md): good-news gaps paid over 5-10 days, not on the day; no bearish bets right after a big name's bad-news gap. Confirm the news from two outlets first: TSLA 10-26 (Barclays upgrade) was skipped at 8:50 on one source, then bought at $394.68 once confirmed and holding +6% above VWAP. Never chase a gap on one unconfirmed source: CEG (+12% gap, -$0.74) is the largest loss.
- Don't cancel an unbought confirm_vwap pick on an early dip: CLF 10-19 dipped -5.6% early, I dropped it, and it finished ~+18% vs Friday. Keep such picks until the stated wrong-if breaks.
- If a capped pick runs past its cap while the tape confirms the thesis, raising the cap once is fine (MMM 10-20: cap $166 to $172, filled $169.74, $173.26 on 10-21).
- Check beat quality before trusting a big EPS beat: ELV 10-21 (adj EPS $6.99 vs ~$4.70, guide raised) gapped to ~$448 and sank to $428 in the first hour; GAAP included a $1.85/share non-operating benefit and membership fell. confirm_vwap kept us out. A post-earnings gap that fades below VWAP in the first hour has twice been the right skip (HUM, ELV); LMT 10-22 (+7.6%, raised guide) stayed below VWAP all day in a -2.7% Nasdaq; the pick was re-issued on day 2, filled at $587.50 once above VWAP, and closed the week at $608.71 (+3.6%). Re-issuing a held-up gap on day 2 with confirm_vwap worked. On a big gap with no live price yet, wait for the 10:20 snapshot: CLS 10-27 (+16% premarket) opened ~+6%, and confirm_vwap bought it at $277.76 once back above VWAP. A gap that fully fades in the first hour is also a sell signal for a position already held (UNH 10-13, +$0.42).

Entry
- Picks execute within minutes as limit orders capped at max_entry_price. Give every gap pick a cap and judge the thesis on the first-hour price. Check state/market.json's as_of_et before setting a cap; on a moving tape set a 3x ETF's cap 2-3% over the snapshot (10-16 SQQQ missed its stale cap).

Exits
- Write a concrete "wrong if" for every pick and act on it at the next refresh (AZZ's ~$132 line, -$0.82; HAL's $33 line, -$0.55). Close on the stated kill condition even before the hold limit.
- A sector tailwind doesn't protect a stock in a broad selloff: HAL fell -4% on 10-22 while Brent hit a five-month high (energy sold with everything).

Direction calls (scalp_bias and same-day SQQQ/TQQQ)
- Bias hit rate 7 of 9 (wrong 10-13 and 10-15; right 10-14, 10-16, 10-20, 10-22, 10-23, 10-26, 10-27; 10-19, 10-21 neutral). Conviction 1 only, with the tape (QQQ vs its open), never fading it; revisit after ~20 scored calls in research/direction_log.csv.
- But with-the-tape same-day trades are net -$0.03 over 4 (10-16 +$0.11, 10-19 -$0.15, 10-20 -$0.11, 10-23 +$0.12 only after an unplanned weekend hold). On 10-20 the call was right (QQQ +0.65% in the window) yet TQQQ lost: bought near the late-morning high (QQQ +0.99% at 11:00), then the rally cooled to +0.4%. 10-23 (QQQ +0.78% at 11:11) repeated it: bought $67.14 near the high, -1% by 15:21. Leaning: the 11:20 entry buys after most of the move; skip it when QQQ is already ~1% up (stretched, as on 10-26) as well as when it's within ~0.5%.
- Headline index levels are often stale; trust state/market.json. Watch yields, not just the print (10-15 PPI: SQQQ -$0.25 as yields fell).

Sizing, regime and process
- Live equity ~$74: conviction 1 is ~$11, 2 is ~$18, 3 is ~$30; one bad pick costs about $1. Reserve conviction 3 for catalysts confirmed by primary sources.
- GitHub's cron is unreliable: it skipped 15:35/15:50 on 10-23 (TQQQ held over the weekend) and ran nothing from the open until 11:10 ET on 10-26. If state/account.json is over ~30 minutes old in market hours, dispatch `trade.yml -f command=cycle` (a bare dispatch only runs "status"). A 15:40 ET check covers same-day exits; avoid same-day picks on Fridays until it has proven itself.
- A run whose state save fails still trades (TSLA 10-26 was adopted with default exits). Since 10-26 the next run rebuilds such a pick from its entry order while the pick is still in picks/latest.json, so keep a bought pick out of "close" lists by its own id; check state/positions.json after new buys.
- Before CPI/FOMC/major event mornings, carrying new picks into the print has had no edge. Puts only fit stocks under ~$15; check the chain.
- Scalper (paper): no after-cost edge; it follows the bias. Tuner tightened its stop to 0.2% on 10-22 (replay +1.87%/+6.43%).
- Overnight SPY core (~$39; idle cash goes to SPY after 14:30 ET, sold as picks need it; size picks as usual, never pick SPY): funds picks as designed (10-23 two sales, 10-26 TSLA); lost ~$0.63 its first night (10-22), roughly flat since. Judge it over weeks, not days.
