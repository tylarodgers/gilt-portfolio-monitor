"""Basic checks that the maths and the rebalancing behave sensibly. Run with: python -m pytest"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from bonds import dv01, macaulay_duration, modified_duration, price  # noqa: E402
from checks import run_checks  # noqa: E402
from portfolio import summary, value_holdings  # noqa: E402
from rebalance import suggest_trades  # noqa: E402
from yields import load_sample_yields, yield_for_maturity  # noqa: E402


def test_bond_priced_at_par_when_coupon_equals_yield():
    assert price(4.0, 10, 4.0) == pytest.approx(100.0, abs=1e-9)


def test_price_falls_when_yield_rises():
    assert price(4.0, 10, 5.0) < price(4.0, 10, 4.0)


def test_duration_shorter_than_maturity_and_dv01_positive():
    assert 0 < modified_duration(4.0, 10, 4.0) < macaulay_duration(4.0, 10, 4.0) < 10
    assert dv01(4.0, 10, 4.0) > 0


def test_dv01_matches_small_yield_move():
    # Bumping the yield by 1bp should change the price by about DV01
    move = price(4.0, 10, 4.0) - price(4.0, 10, 4.01)
    assert move == pytest.approx(dv01(4.0, 10, 4.0), rel=1e-3)


def test_curve_interpolation():
    curve = pd.Series({5: 4.0, 10: 5.0, 20: 6.0})
    assert yield_for_maturity(curve, 7.5) == pytest.approx(4.5)
    assert yield_for_maturity(curve, 2) == 4.0   # flat below 5y
    assert yield_for_maturity(curve, 30) == 6.0  # flat beyond 20y


def test_suggested_trades_clear_all_breaches_on_sample_data():
    rules = json.loads((ROOT / "data" / "guidelines.json").read_text())
    yields = load_sample_yields()
    curve, as_of = yields.iloc[-1], yields.index[-1]
    port = value_holdings(pd.read_csv(ROOT / "data" / "portfolio.csv"), curve, as_of)
    bench = value_holdings(pd.read_csv(ROOT / "data" / "benchmark.csv"), curve, as_of)
    bench_sum = summary(bench)
    before = run_checks(port, summary(port, rules["cash_gbp"]), bench, bench_sum, rules)
    _, after_port, after_cash = suggest_trades(port, rules["cash_gbp"], bench_sum, rules)
    after = run_checks(after_port, summary(after_port, after_cash), bench, bench_sum, rules)
    assert (before.status == "BREACH").any()
    assert not (after.status == "BREACH").any()
    # Trades should leave the fund's total value unchanged
    assert summary(after_port, after_cash)["total_value_gbp"] == pytest.approx(
        summary(port, rules["cash_gbp"])["total_value_gbp"])
