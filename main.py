"""V-bottom dip bot for make.fun btc-race-24h-20261118-1444.

Trades cbBTC/USDC 1-minute bars, long only, starting from 1,000 USDC paper.
The dev window (24h, BTC -2.80%, range 63,076-65,190) is a falling,
choppy tape: 1-minute return stdev 0.067%, worst 60-minute drop -2.31%
(bar 68), best 60-minute rise only +1.19% (bar 507). On it, shallow-dip
and rolling-high dip-buying LOSE (they buy into the grind and bleed on
fees: -11 to -19 USDC), momentum ignition LOSES (-4 to -17 USDC), and
the slow-EMA dip ladder that won yesterday only makes +2 to +9 USDC
(the falling tape keeps the price below the EMA without bouncing).
What works is buying a genuine excursion: the close 1.6% below the
highest close of the last 300 minutes, with the whole cash, and selling
the bounce at +1.8% over the average entry (or -1.2% stop, or after
300 bars). Two round trips on the dev window, both winners, max
drawdown 0.65%.

Grid-searched on the dev window with an exact local replay harness, picked
for robustness, not dev rank: the parameters sit on a plateau
(dip 0.015-0.016, TP 0.018-0.020, hold 240-360 all give +21 to +24 USDC),
and every stress check stays positive (first half +17.80, -1% drift
+21.36, +1% drift +21.36). Hold 300 was chosen over 240 (+21.36) and
360 (+24.38) as the middle of the plateau: trip 2 exits on the hold
timeout, and a longer hold only helps while the bounce keeps drifting
up, which the race window may not do. The stop never triggers on the
dev window; it is a safety net only. The final race window is unseen,
so the bot is deliberately selective: if the race window has no 1.6%
excursion below its 300-bar high it stays in cash rather than bleeding
out in the grind.

Entry price is the position's average cost from the account state (never
an assumed price). All decisions are pure functions of the bar stream:
no clock, no environment, no randomness, so two runs agree byte for byte.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = None  # set from hello: the competition's single symbol
LOOKBACK = 300  # rolling-high window: 300 one-minute closes (~5 hours)
DIP = 0.016  # buy when the close is this far below the 300-bar high
TAKE_PROFIT = 0.018  # sell when close is this far above the average entry
STOP_LOSS = 0.012  # sell when close is this far below the average entry
MAX_HOLD = 300  # sell after this many bars held, whatever the price
MAX_SLIPPAGE_BPS = 200  # 2%: covers the largest 1-minute move seen (~0.65%)
NO_BUY_AFTER_BARS = 1380  # stop opening with 60 bars left in the window

_closes = []  # closes of scored bars, oldest first
_buy_bar = 0  # scored bar of the buy that opened the position


def on_hello(state):
    global SYMBOL
    SYMBOL = state.hello["symbols"][0]["symbol"]


def _avg_entry_price(state):
    """Average entry price of the open position, in raw price units.

    cost is quote units spent, qty is qty-scale units, price is
    price-scale units: value(qty, p) = qty * p * 10^6 / 10^13.
    """
    holding = state.positions.get(SYMBOL)
    if holding is None or holding.qty <= 0:
        return None
    return holding.cost * 10 ** 13 // (holding.qty * 10 ** 6)


def on_batch(state, batch):
    global _buy_bar
    if state.warming_up:
        return []
    bar = None
    for b in batch.get("bars", []):
        if b.get("symbol") == SYMBOL:
            bar = b
            break
    if bar is None:
        return []
    close = int(bar["c"])
    _closes.append(close)

    holding = state.positions.get(SYMBOL)
    if holding is not None and holding.qty > 0:
        avg = _avg_entry_price(state)
        if avg is not None:
            if close >= avg * (1.0 + TAKE_PROFIT):
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            if close <= avg * (1.0 - STOP_LOSS):
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            if state.seq - _buy_bar >= MAX_HOLD:
                return [{"side": "sell", "symbol": SYMBOL, "qty": holding.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
        return []

    # Flat: buy the whole cash on a deep dip below the 300-bar high.
    if state.seq >= NO_BUY_AFTER_BARS:
        return []
    if len(_closes) < LOOKBACK + 2:
        return []
    high = max(_closes[-LOOKBACK:])
    if close <= high * (1.0 - DIP):
        _buy_bar = state.seq
        notional = state.cash
        if notional >= 1_000_000:
            return [{"side": "buy", "symbol": SYMBOL,
                     "notional_quote_units": notional,
                     "max_slippage_bps": MAX_SLIPPAGE_BPS,
                     "client_id": state.client_id()}]
    return []


makefun_bars.run(on_batch, on_hello=on_hello)
