"""Load a portfolio or benchmark file and value every holding off today's yield curve."""
from datetime import date

import pandas as pd

from bonds import dv01, modified_duration, price
from yields import yield_for_maturity


def years_to(maturity: pd.Timestamp, as_of: date) -> float:
    return (pd.Timestamp(maturity) - pd.Timestamp(as_of)).days / 365.25


def value_holdings(holdings: pd.DataFrame, curve: pd.Series, as_of: date) -> pd.DataFrame:
    """Add yield, price, market value, weight, duration and DV01 to each holding.

    holdings needs columns: bond, coupon_pct, maturity, nominal_gbp
    """
    df = holdings.copy()
    df["nominal_gbp"] = df["nominal_gbp"].astype(float)
    df["maturity"] = pd.to_datetime(df["maturity"])
    df["years"] = df["maturity"].apply(lambda m: years_to(m, as_of))
    df["yield_pct"] = df["years"].apply(lambda t: yield_for_maturity(curve, t))
    df["price"] = df.apply(lambda r: price(r.coupon_pct, r.years, r.yield_pct), axis=1)
    df["market_value_gbp"] = df["nominal_gbp"] * df["price"] / 100
    df["weight_pct"] = 100 * df["market_value_gbp"] / df["market_value_gbp"].sum()
    df["mod_duration"] = df.apply(lambda r: modified_duration(r.coupon_pct, r.years, r.yield_pct), axis=1)
    # DV01 in pounds: how much the holding gains/loses for a 1bp move in yields
    df["dv01_gbp"] = df.apply(lambda r: dv01(r.coupon_pct, r.years, r.yield_pct) * r.nominal_gbp / 100, axis=1)
    return df


def summary(valued: pd.DataFrame, cash_gbp: float = 0.0) -> dict:
    bonds_mv = valued["market_value_gbp"].sum()
    total = bonds_mv + cash_gbp
    return {
        "total_value_gbp": total,
        "bonds_value_gbp": bonds_mv,
        "cash_gbp": cash_gbp,
        "cash_pct": 100 * cash_gbp / total if total else 0.0,
        # Duration of the whole fund, counting cash as zero duration
        "mod_duration": (valued["mod_duration"] * valued["market_value_gbp"]).sum() / total,
        "dv01_gbp": valued["dv01_gbp"].sum(),
        "avg_yield_pct": (valued["yield_pct"] * valued["market_value_gbp"]).sum() / bonds_mv,
    }


def bucket_weights(valued: pd.DataFrame, total_value: float) -> pd.Series:
    """% of the fund in each maturity bucket."""
    bins = [0, 5, 10, 15, 100]
    labels = ["0-5y", "5-10y", "10-15y", "15y+"]
    buckets = pd.cut(valued["years"], bins=bins, labels=labels)
    return (valued.groupby(buckets, observed=False)["market_value_gbp"].sum() / total_value * 100).reindex(labels)
