"""Suggest trades that bring the portfolio back inside its guidelines.

These are suggestions for a Portfolio Manager to approve, not orders.
Order of steps:
  1. Trim any bond above the single-bond cap (proceeds go to cash).
  2. Bring cash back to its target level (invest the excess, or raise cash).
  3. Close the duration gap to the benchmark with a cash-neutral "switch":
     sell the longest bond and buy the shortest (or the reverse), same value each side.
"""
import pandas as pd

from portfolio import summary


def _mv_to_nominal(mv, px):
    return mv * 100 / px


def suggest_trades(port: pd.DataFrame, cash: float, bench_sum: dict, rules: dict):
    """Return (trades table, holdings after trades, cash after trades)."""
    p = port.copy()
    trades = []

    def trade(i, mv_change, reason):
        nonlocal cash
        px = p.at[i, "price"]
        p.at[i, "market_value_gbp"] += mv_change
        p.at[i, "nominal_gbp"] += _mv_to_nominal(mv_change, px)
        cash -= mv_change
        trades.append({
            "action": "BUY" if mv_change > 0 else "SELL",
            "bond": p.at[i, "bond"],
            "nominal_gbp": round(abs(_mv_to_nominal(mv_change, px)), -3),
            "market_value_gbp": round(abs(mv_change), -3),
            "reason": reason,
        })

    total = p["market_value_gbp"].sum() + cash

    # 1. Concentration
    cap = rules["max_single_bond_pct"] / 100 * total
    for i in p.index:
        excess = p.at[i, "market_value_gbp"] - cap
        if excess > 0:
            trade(i, -excess, f"Trim to {rules['max_single_bond_pct']}% single-bond limit")

    # 2. Cash back to target (midpoint of the allowed range)
    target_cash = (rules["min_cash_pct"] + rules["max_cash_pct"]) / 2 / 100 * total
    gap_cash = cash - target_cash
    if gap_cash > 0.005 * total:
        # Invest excess cash, starting with the bond whose duration is closest to the benchmark
        # (so this step barely moves duration), without pushing any bond over the cap.
        order = (p["mod_duration"] - bench_sum["mod_duration"]).abs().sort_values().index
        for i in order:
            room = cap - p.at[i, "market_value_gbp"]
            amount = min(gap_cash, room)
            if amount > 0.001 * total:
                trade(i, amount, "Invest excess cash")
                gap_cash -= amount
            if gap_cash <= 0.001 * total:
                break
    elif gap_cash < -0.005 * total:
        i = (p["mod_duration"] - bench_sum["mod_duration"]).abs().idxmin()
        trade(i, gap_cash, "Raise cash to target")

    # 3. Duration switch, aiming at the benchmark's duration
    def fund_duration():
        return (p["mod_duration"] * p["market_value_gbp"]).sum() / total

    gap = fund_duration() - bench_sum["mod_duration"]
    if abs(gap) > 0.05:
        long_i, short_i = p["mod_duration"].idxmax(), p["mod_duration"].idxmin()
        spread = p.at[long_i, "mod_duration"] - p.at[short_i, "mod_duration"]
        switch = gap * total / spread  # market value to move from long to short (negative = the reverse)
        if gap > 0:
            switch = min(switch, p.at[long_i, "market_value_gbp"], cap - p.at[short_i, "market_value_gbp"])
            trade(long_i, -switch, "Shorten duration towards benchmark")
            trade(short_i, switch, "Shorten duration towards benchmark")
        else:
            switch = min(-switch, p.at[short_i, "market_value_gbp"], cap - p.at[long_i, "market_value_gbp"])
            trade(short_i, -switch, "Lengthen duration towards benchmark")
            trade(long_i, switch, "Lengthen duration towards benchmark")

    # Recalculate weights and DV01 after trades (duration per bond doesn't change)
    p["weight_pct"] = 100 * p["market_value_gbp"] / p["market_value_gbp"].sum()
    p["dv01_gbp"] = p["mod_duration"] * p["market_value_gbp"] / 10_000

    return pd.DataFrame(trades), p, cash


def post_trade_summary(p, cash):
    return summary(p, cash)
