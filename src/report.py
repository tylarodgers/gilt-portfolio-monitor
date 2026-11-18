"""Write the monitoring results to a formatted Excel workbook."""
import pandas as pd
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEADER_FILL = PatternFill("solid", fgColor="1F3864")
PASS_FILL = PatternFill("solid", fgColor="D9EAD3")
BREACH_FILL = PatternFill("solid", fgColor="F4CCCC")


def _format_sheet(ws, money_cols=(), pct_cols=(), num_cols=()):
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    headers = [c.value for c in ws[1]]
    for idx, name in enumerate(headers, start=1):
        letter = get_column_letter(idx)
        width = max(len(str(name)), *(len(str(c.value)) for c in ws[letter][1:]), 8)
        ws.column_dimensions[letter].width = min(width + 2, 70)
        fmt = None
        if name in money_cols:
            fmt = "£#,##0"
        elif name in pct_cols:
            fmt = "0.00"
        elif name in num_cols:
            fmt = "0.000"
        if fmt:
            for c in ws[letter][1:]:
                c.number_format = fmt
    ws.freeze_panes = "A2"


def _colour_status(ws):
    headers = [c.value for c in ws[1]]
    if "status" not in headers:
        return
    col = headers.index("status") + 1
    for row in ws.iter_rows(min_row=2, min_col=col, max_col=col):
        for c in row:
            c.fill = PASS_FILL if c.value == "PASS" else BREACH_FILL
            c.font = Font(bold=True)


def write_report(path, as_of, source, pre_sum, bench_sum, post_sum,
                 positions, checks_pre, trades, checks_post, yields):
    money = ["nominal_gbp", "market_value_gbp", "dv01_gbp"]
    pct = ["weight_pct", "yield_pct", "price", "coupon_pct"]
    num = ["years", "mod_duration"]

    summary_rows = [
        ("Report date", as_of.strftime("%d %b %Y"), "", ""),
        ("Yield data source", source, "", ""),
        ("", "", "", ""),
        ("Metric", "Portfolio now", "Benchmark", "Portfolio after suggested trades"),
        ("Total value (£)", pre_sum["total_value_gbp"], bench_sum["total_value_gbp"], post_sum["total_value_gbp"]),
        ("Modified duration (yrs)", pre_sum["mod_duration"], bench_sum["mod_duration"], post_sum["mod_duration"]),
        ("DV01 (£ per 1bp)", pre_sum["dv01_gbp"], bench_sum["dv01_gbp"], post_sum["dv01_gbp"]),
        ("Average yield (%)", pre_sum["avg_yield_pct"], bench_sum["avg_yield_pct"], post_sum["avg_yield_pct"]),
        ("Cash (%)", pre_sum["cash_pct"], bench_sum["cash_pct"], post_sum["cash_pct"]),
        ("", "", "", ""),
        ("Guideline breaches now", int((checks_pre["status"] == "BREACH").sum()), "", ""),
        ("Guideline breaches after suggested trades", int((checks_post["status"] == "BREACH").sum()), "", ""),
    ]

    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        pd.DataFrame(summary_rows).to_excel(xw, sheet_name="Summary", index=False, header=False)
        checks_pre.to_excel(xw, sheet_name="Guideline checks", index=False)
        (trades if not trades.empty else pd.DataFrame([{"action": "None needed"}])).to_excel(
            xw, sheet_name="Suggested trades", index=False)
        checks_post.to_excel(xw, sheet_name="Checks after trades", index=False)
        positions.to_excel(xw, sheet_name="Positions", index=False)
        yields.reset_index().rename(columns={5: "5y", 10: "10y", 20: "20y"}).to_excel(
            xw, sheet_name="Yield history", index=False)

        wb = xw.book
        # Summary sheet formatting
        ws = wb["Summary"]
        ws.column_dimensions["A"].width = 42
        for col in "BCD":
            ws.column_dimensions[col].width = 30
        for c in ws[4]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = HEADER_FILL
        ws["A1"].font = Font(bold=True)
        ws["A2"].font = Font(bold=True)
        formats = {5: "£#,##0", 6: "0.00", 7: "£#,##0", 8: "0.00", 9: "0.0"}
        for r, fmt in formats.items():
            for col in "BCD":
                ws[f"{col}{r}"].number_format = fmt
        for r in (11, 12):
            ws[f"A{r}"].font = Font(bold=True)
            ws[f"B{r}"].fill = BREACH_FILL if ws[f"B{r}"].value else PASS_FILL

        for name in ("Guideline checks", "Checks after trades"):
            _format_sheet(wb[name])
            _colour_status(wb[name])
        _format_sheet(wb["Suggested trades"], money_cols=money)
        _format_sheet(wb["Positions"], money_cols=money, pct_cols=pct, num_cols=num)
        for c in wb["Positions"]["C"][1:]:
            c.number_format = "dd-mmm-yyyy"

        ys = wb["Yield history"]
        _format_sheet(ys, pct_cols=["5y", "10y", "20y"])
        for c in ys["A"][1:]:
            c.number_format = "dd-mmm-yyyy"
        ys.column_dimensions["A"].width = 14
        chart = LineChart()
        chart.title = "UK gilt yields (%)"
        chart.y_axis.title = "Yield (%)"
        chart.height, chart.width = 9, 20
        n = ys.max_row
        chart.add_data(Reference(ys, min_col=2, max_col=4, min_row=1, max_row=n), titles_from_data=True)
        chart.set_categories(Reference(ys, min_col=1, min_row=2, max_row=n))
        chart.x_axis.number_format = "mmm-yy"
        chart.y_axis.scaling.min = max(0, int(yields.min().min()) - 1)
        chart.y_axis.scaling.max = int(yields.max().max()) + 1
        wb["Summary"].add_chart(chart, "A15")
