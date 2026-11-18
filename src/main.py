"""Gilt portfolio monitor: value a portfolio, check guidelines, suggest trades, write a report.

Run from the project folder:
    python src/main.py              # tries the Bank of England first
    python src/main.py --sample     # uses the bundled sample yields (no internet needed)
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from checks import run_checks
from portfolio import summary, value_holdings
from rebalance import post_trade_summary, suggest_trades
from report import write_report
from yields import get_yields

ROOT = Path(__file__).resolve().parent.parent
DATA, OUT = ROOT / "data", ROOT / "output"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sample", action="store_true", help="use bundled sample yields instead of downloading")
    args = ap.parse_args()

    rules = json.loads((DATA / "guidelines.json").read_text())
    yields, source = get_yields(use_sample=args.sample)
    as_of = yields.index[-1]
    curve = yields.iloc[-1]
    print(f"Yield curve on {as_of:%d %b %Y} ({source}): "
          + ", ".join(f"{k}y {v:.2f}%" for k, v in curve.items()))

    port_raw = pd.read_csv(DATA / "portfolio.csv")
    bench_raw = pd.read_csv(DATA / "benchmark.csv")
    port = value_holdings(port_raw, curve, as_of)
    bench = value_holdings(bench_raw, curve, as_of)
    port_sum = summary(port, rules["cash_gbp"])
    bench_sum = summary(bench, 0.0)

    checks_pre = run_checks(port, port_sum, bench, bench_sum, rules)
    trades, port_after, cash_after = suggest_trades(port, rules["cash_gbp"], bench_sum, rules)
    post_sum = post_trade_summary(port_after, cash_after)
    checks_post = run_checks(port_after, post_sum, bench, bench_sum, rules)

    OUT.mkdir(exist_ok=True)
    out_file = OUT / f"portfolio_report_{as_of:%Y-%m-%d}.xlsx"
    cols = ["bond", "coupon_pct", "maturity", "nominal_gbp", "years", "yield_pct", "price",
            "market_value_gbp", "weight_pct", "mod_duration", "dv01_gbp"]
    write_report(out_file, as_of, source, port_sum, bench_sum, post_sum,
                 port[cols], checks_pre, trades, checks_post, yields)

    print(f"\nPortfolio duration {port_sum['mod_duration']:.2f} yrs vs benchmark {bench_sum['mod_duration']:.2f} yrs")
    print(f"Breaches now: {(checks_pre.status == 'BREACH').sum()}  |  "
          f"after suggested trades: {(checks_post.status == 'BREACH').sum()}")
    if not trades.empty:
        print("\nSuggested trades (for PM approval):")
        print(trades.to_string(index=False))
    print(f"\nReport saved to {out_file}")


if __name__ == "__main__":
    main()
