"""Bond maths: price, modified duration and DV01 for a fixed-coupon bond.

Gilts pay coupons twice a year, so we discount on a semi-annual basis.
Simplification: we treat the bond as if today is a coupon date (no accrued interest).
That is fine for a monitoring tool; a production system would use exact day counts.
"""


def cash_flows(coupon_pct: float, years: float, freq: int = 2, face: float = 100.0):
    """List of (time in years, cash flow) for a bond with `years` left to maturity."""
    n = max(1, round(years * freq))
    c = face * coupon_pct / 100 / freq
    flows = [(i / freq, c) for i in range(1, n + 1)]
    t_last, c_last = flows[-1]
    flows[-1] = (t_last, c_last + face)  # principal repaid at maturity
    return flows


def price(coupon_pct: float, years: float, yield_pct: float, freq: int = 2) -> float:
    """Clean price per 100 face value, given the yield in % per year."""
    y = yield_pct / 100 / freq
    return sum(cf / (1 + y) ** (t * freq) for t, cf in cash_flows(coupon_pct, years, freq))


def macaulay_duration(coupon_pct: float, years: float, yield_pct: float, freq: int = 2) -> float:
    """Weighted-average time (years) until the bond's cash flows are received."""
    y = yield_pct / 100 / freq
    p = price(coupon_pct, years, yield_pct, freq)
    return sum(t * cf / (1 + y) ** (t * freq) for t, cf in cash_flows(coupon_pct, years, freq)) / p


def modified_duration(coupon_pct: float, years: float, yield_pct: float, freq: int = 2) -> float:
    """% change in price for a 1 percentage-point (100bp) move in yield."""
    return macaulay_duration(coupon_pct, years, yield_pct, freq) / (1 + yield_pct / 100 / freq)


def dv01(coupon_pct: float, years: float, yield_pct: float, freq: int = 2) -> float:
    """Change in price (per 100 face) for a 0.01% (1 basis point) move in yield."""
    return modified_duration(coupon_pct, years, yield_pct, freq) * price(coupon_pct, years, yield_pct, freq) / 10_000
