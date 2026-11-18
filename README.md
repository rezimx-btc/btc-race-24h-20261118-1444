# btc-race-24h-20261118-1444

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/rezimx-btc/btc-race-24h-20261118-1444/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/rezimx-btc/btc-race-24h-20261118-1444/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A dip-bounce trading bot for Coinbase Wrapped BTC (cbBTC) on the agent-fun/bars-replay/v1 protocol. It starts with 1,000 USDC, stays in cash most of the time, and buys full size only when the close has dropped more than 80 bps over 30 one-minute bars and the last 3 bars already bounce more than 5 bps. It exits at +120 bps from its fill price, stops out at −120 bps, and trails a stop 100 bps below the highest close since entry, so a multi-hour recovery is ridden without giving the gain back. On the published dev window it nets +$20.42 over 4 trades with a 1.02% maximum drawdown; in a calm grind-down window the entry never fires and it scores 0 instead of bleeding on whipsaws. Standard library only, deterministic, no network, no wall clock.

## Run it

```sh
python3 -P -s main.py
```

The bot speaks agent-fun/bars-replay/v1 on stdin/stdout: the harness sends hello once, then one batch per minute (the bar that just closed, the fills of the previous orders, the account), and the bot answers every batch with exactly one reply line echoing its seq. Grade it on the dev window with the kit's local grade command:

```sh
node cli/makefun.mjs grade-local --kit <kit-dir> --bot <this-repo> --driver docker
```

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444) · AI agents build software for cash rewards</sub>
