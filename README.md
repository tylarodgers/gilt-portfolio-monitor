# Gilt Portfolio Monitor

A small Python tool that does the daily checks a fixed income portfolio team runs on a bond fund:

1. **Gets the UK gilt yield curve.** Downloads daily 5, 10 and 20-year nominal par yields from the Bank of England database.
2. **Values the portfolio and a benchmark.** Prices each gilt off the curve and works out market value, weight, modified duration and DV01.
3. **Checks client guidelines.** Duration against the benchmark, single-bond limits, cash range and maturity-bucket weights. Each rule comes back as PASS or BREACH.
4. **Suggests corrective trades.** These are for Portfolio Manager approval: trim oversized positions, put excess cash to work, and run a switch trade to close the duration gap.
5. **Writes an Excel report.** It has a summary, a yield chart, guideline checks before and after the trades, suggested trades and full positions.

See `examples/example_report.xlsx` for a sample output.

## Quick start

```bash
pip install -r requirements.txt
python src/main.py            # downloads live yields from the Bank of England
python src/main.py --sample   # uses the bundled sample yields (works offline)
python -m pytest              # runs the tests
```

The report is saved in `output/`.

## Changing the inputs

| File | What it holds |
| --- | --- |
| `data/portfolio.csv` | Holdings: bond name, coupon %, maturity date, nominal (£) |
| `data/benchmark.csv` | The benchmark, in the same format |
| `data/guidelines.json` | Cash held and the client rules (duration tolerance, max % per bond, cash range, bucket tolerance) |

The sample portfolio starts with six breaches (duration too long, two oversized positions, too much cash, and two maturity buckets off benchmark). After the suggested trades it has none.

## How it works

| Module | Job |
| --- | --- |
| `src/yields.py` | Bank of England download, with a fallback to sample data and linear curve interpolation |
| `src/bonds.py` | Price, Macaulay and modified duration, and DV01 for semi-annual coupon bonds |
| `src/portfolio.py` | Values holdings and calculates fund-level duration, DV01 and maturity buckets |
| `src/checks.py` | Guideline rules |
| `src/rebalance.py` | Trade suggestions |
| `src/report.py` | Formatted Excel output |

## Simplifications

This is a learning and portfolio project, not a production system:
- Bonds are named "illustrative" and are not real gilt ISINs.
- Pricing assumes today is a coupon date, so there's no accrued interest and no exact day count.
- The curve is three points linearly interpolated, rather than a fitted spline.
- `data/sample_gilt_yields.csv` is **synthetic** data used only when the live download fails. The report states which source was used.
