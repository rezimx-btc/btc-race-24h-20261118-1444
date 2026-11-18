"""Dip-bounce BTC bot for agent-fun/bars-replay/v1 (make.fun btc-race-24h-20261118-1444).

Strategy (designed from the kit rules, tuned on the dev window's 1-minute bars):
  * The dev window falls 2.8% overall, so buy-and-hold loses; 1-minute noise is
    ~7 bps, so a round trip costs ~26 bps in fees, slippage and price impact.
  * Entry: buy full size when the close has dropped more than 80 bps over the
    last 30 bars AND the last 3 bars already bounce more than 5 bps. The dip
    alone is not enough in a falling market; the bounce is the confirmation
    that sellers are exhausted.
  * Exit: take profit at +120 bps from the fill price, stop loss at -120 bps,
    and a trailing stop 100 bps below the highest close since entry, so a
    multi-hour recovery is ridden but a reversal does not give the gain back.
  * Otherwise stay in cash. In a calm grind-down window the entry never fires
    and the bot scores exactly 0 instead of bleeding on whipsaws.

Wire protocol: the harness sends hello once, then one batch per minute (the
bar that just closed, the fills of the previous orders, the account), then
done. This bot answers every batch with exactly one reply line echoing its
seq, carrying at most one order. Orders decided on a batch fill at the next
bar's open. All decisions use integer price units from the bars; no wall
clock, no randomness, no files, no network, so two runs on the same data
produce identical orders.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = None  # set from hello: the universe's single symbol

# Strategy constants, in basis points (1 bp = 0.01%).
DROP_WINDOW = 30        # bars over which the dip is measured
DROP_BPS = 80           # entry: 30-bar return below -80 bps
BOUNCE_WINDOW = 3       # bars over which the bounce is measured
BOUNCE_BPS = 5          # entry: 3-bar return above +5 bps
TARGET_BPS = 120        # exit: fill price +120 bps
STOP_BPS = 120          # exit: fill price -120 bps
TRAIL_BPS = 100         # exit: 100 bps below the peak close since entry
MAX_SLIPPAGE_BPS = 500  # cap on fill vs latest close (impact + slippage fit inside)

# Rolling state, kept across batches.
closes = []             # closes in integer price units, oldest first
entry_price = None      # fill price of the open position (int price units)
peak_close = None       # highest close since entry (int price units)
pending_sell = False    # a sell order was sent and not yet reported filled


def bps_return(now, then):
    """(now / then - 1) in basis points, integer math, truncated toward zero."""
    if then <= 0:
        return 0
    diff = (now - then) * 10000
    return diff // then if diff >= 0 else -((-diff) // then)


def on_hello(state):
    global SYMBOL
    SYMBOL = state.hello["symbols"][0]["symbol"]


def on_batch(state, batch):
    global entry_price, peak_close, pending_sell

    # Reconcile with the fills this batch reports: a buy fill opens the
    # position (record its fill price), a sell fill closes it.
    for fill in batch.get("fills", []):
        if fill.get("symbol") != SYMBOL:
            continue
        if fill.get("side") == "sell" and fill.get("status") == "rejected":
            # The sell did not land (e.g. max_slippage on a sharp move):
            # clear the flag so the bot retries the exit on the next bar
            # instead of riding the position to the end-of-window flatten.
            pending_sell = False
            continue
        if fill.get("status") != "filled":
            continue
        if fill.get("side") == "buy":
            entry_price = int(fill["price"])
            peak_close = entry_price
            pending_sell = False
        elif fill.get("side") == "sell":
            entry_price = None
            peak_close = None
            pending_sell = False

    bar = state.latest.get(SYMBOL)
    if bar is None:
        return []
    close = int(bar["c"])
    closes.append(close)
    if len(closes) > 400:
        del closes[: len(closes) - 400]

    holding = state.positions.get(SYMBOL)
    qty = holding.qty if holding is not None else 0

    # If the account says the position is gone (flattened or sold), clear state.
    if qty == 0:
        entry_price = None
        peak_close = None
        pending_sell = False

    if state.warming_up:
        return []

    # --- exit logic, while holding ---
    if qty > 0 and entry_price is not None and not pending_sell:
        if close > peak_close:
            peak_close = close
        ret = bps_return(close, entry_price)
        giveback = bps_return(peak_close, close)
        if ret >= TARGET_BPS or ret <= -STOP_BPS or giveback >= TRAIL_BPS:
            pending_sell = True
            return [
                {
                    "side": "sell",
                    "symbol": SYMBOL,
                    "qty": qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }
            ]
        return []

    # --- entry logic, flat ---
    if qty == 0 and len(closes) > DROP_WINDOW:
        drop = bps_return(close, closes[-1 - DROP_WINDOW])
        bounce = bps_return(close, closes[-1 - BOUNCE_WINDOW])
        if drop < -DROP_BPS and bounce > BOUNCE_BPS:
            # Full-size buy: spend all cash (the cap allows 100% of equity).
            notional = state.cash
            if notional >= 1_000_000:  # at least 1 USDC, the minimum notional
                return [
                    {
                        "side": "buy",
                        "symbol": SYMBOL,
                        "notional_quote_units": notional,
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    }
                ]
    return []


makefun_bars.run(on_batch, on_hello=on_hello)
