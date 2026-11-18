"""Client guideline checks: is the portfolio inside its rules?"""
import pandas as pd

from portfolio import bucket_weights


def run_checks(port, port_sum, bench, bench_sum, rules) -> pd.DataFrame:
    """Return one row per rule with the current value, the limit and PASS/BREACH."""
    rows = []

    # 1. Duration close to benchmark
    gap = port_sum["mod_duration"] - bench_sum["mod_duration"]
    tol = rules["duration_tolerance_years"]
    rows.append({
        "rule": f"Duration within ±{tol} yrs of benchmark",
        "current": f"{port_sum['mod_duration']:.2f} yrs (benchmark {bench_sum['mod_duration']:.2f}, gap {gap:+.2f})",
        "limit": f"±{tol} yrs",
        "status": "PASS" if abs(gap) <= tol else "BREACH",
    })

    # 2. No single bond too big
    cap = rules["max_single_bond_pct"]
    w = 100 * port["market_value_gbp"] / port_sum["total_value_gbp"]
    for bond, weight in zip(port["bond"], w):
        rows.append({
            "rule": f"Max {cap}% in one bond: {bond}",
            "current": f"{weight:.1f}%",
            "limit": f"<= {cap}%",
            "status": "PASS" if weight <= cap + 1e-6 else "BREACH",
        })

    # 3. Cash within a range
    lo, hi = rules["min_cash_pct"], rules["max_cash_pct"]
    rows.append({
        "rule": f"Cash between {lo}% and {hi}%",
        "current": f"{port_sum['cash_pct']:.1f}%",
        "limit": f"{lo}%-{hi}%",
        "status": "PASS" if lo <= port_sum["cash_pct"] <= hi else "BREACH",
    })

    # 4. Maturity buckets close to benchmark
    btol = rules["bucket_tolerance_pct"]
    pb = bucket_weights(port, port_sum["total_value_gbp"])
    bb = bucket_weights(bench, bench_sum["total_value_gbp"])
    for bucket in pb.index:
        diff = pb[bucket] - bb[bucket]
        rows.append({
            "rule": f"{bucket} bucket within ±{btol}pp of benchmark",
            "current": f"{pb[bucket]:.1f}% (benchmark {bb[bucket]:.1f}%, diff {diff:+.1f}pp)",
            "limit": f"±{btol}pp",
            "status": "PASS" if abs(diff) <= btol else "BREACH",
        })

    return pd.DataFrame(rows)
