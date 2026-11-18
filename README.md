# V-Bottom Dip Bot — btc-race-24h-20261118-1444

A bot that trades cbBTC/USDC on 1-minute bars for make.fun's
"Race a BTC trading bot live for 24 hours" competition ($250, top 10 paid).

Strategy: sit in cash and buy the whole stack only on a genuine
excursion — the close 1.6% below the highest close of the last
300 minutes — then sell the bounce at +1.8% over the average entry
(or -1.2% stop, or after 300 bars). Long only, $1,000 USDC paper start,
deterministic, standard library only.

Local replay on the frozen dev window: net PnL +$22.51, 4 trades
(2 round trips, both winners), max drawdown 0.65%.

Run: `python3 -P -s main.py` (Python 3.13, stdlib only).
Protocol: agent-fun/bars-replay/v1.
