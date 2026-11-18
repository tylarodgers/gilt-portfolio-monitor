"""Get UK gilt yields: download from the Bank of England, or fall back to a local sample file.

The Bank of England publishes daily nominal par yields for UK government bonds (gilts).
We use three points on the curve:
    IUDSNPY = 5-year, IUDMNPY = 10-year, IUDLNPY = 20-year nominal par yield (% per year).
"""
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BOE_URL = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
SERIES = {"IUDSNPY": 5, "IUDMNPY": 10, "IUDLNPY": 20}  # series code -> maturity in years
SAMPLE_FILE = Path(__file__).resolve().parent.parent / "data" / "sample_gilt_yields.csv"


def download_boe_yields(start="01/Jan/2023", timeout=20) -> pd.DataFrame:
    """Download daily gilt yields from the Bank of England database.

    Returns a table indexed by date with one column per maturity (5, 10, 20).
    """
    params = {
        "csv.x": "yes",
        "Datefrom": start,
        "Dateto": "now",
        "SeriesCodes": ",".join(SERIES),
        "CSVF": "TN",       # tabular, no titles
        "UsingCodes": "Y",
        "VPD": "Y",
        "VFD": "N",
    }
    # The BoE site can refuse requests that don't look like a browser.
    headers = {"User-Agent": "Mozilla/5.0 (gilt-portfolio-monitor)"}
    resp = requests.get(BOE_URL, params=params, headers=headers, timeout=timeout)
    resp.raise_for_status()

    df = pd.read_csv(StringIO(resp.text))
    df["DATE"] = pd.to_datetime(df["DATE"], format="%d %b %Y")
    df = df.set_index("DATE").rename(columns=SERIES).sort_index()
    return df[[5, 10, 20]].astype(float).dropna()


def load_sample_yields() -> pd.DataFrame:
    df = pd.read_csv(SAMPLE_FILE, parse_dates=["DATE"]).set_index("DATE")
    df.columns = [int(c) for c in df.columns]
    return df


def get_yields(use_sample=False):
    """Return (yield history, source label). Tries the Bank of England first."""
    if not use_sample:
        try:
            return download_boe_yields(), "Bank of England (live download)"
        except Exception as exc:  # no internet, site change, etc.
            print(f"Could not download from the Bank of England ({exc}). Using the sample file instead.")
    return load_sample_yields(), "Sample data (synthetic, for testing only)"


def yield_for_maturity(curve: pd.Series, years: float) -> float:
    """Linear interpolation on the curve; flat beyond the shortest/longest point.

    curve: one day's yields, e.g. {5: 3.9, 10: 4.4, 20: 4.9} in %.
    Returns the yield in % for the given years to maturity.
    """
    xs = np.array(sorted(curve.index), dtype=float)
    ys = np.array([curve[x] for x in sorted(curve.index)], dtype=float)
    return float(np.interp(years, xs, ys))
