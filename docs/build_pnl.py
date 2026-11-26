"""Build docs/business_model_pnl.xlsx: assumptions, unit economics, 24-month P&L (live formulas)."""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

OUT = Path(__file__).resolve().parent / "business_model_pnl.xlsx"
MONTHS = 24
BLUE = Font(color="0000FF")  # inputs
BOLD = Font(bold=True)
HEAD = PatternFill("solid", fgColor="DDEBF7")
USD = '$#,##0;[Red]-$#,##0'
USD2 = '$#,##0.00;[Red]-$#,##0.00'
PCT = '0.0%'

wb = Workbook()

# ---------------- Assumptions ----------------
A = wb.active
A.title = "Assumptions"
A["A1"] = "Assumptions (blue = input; change these, everything else recalculates)"
A["A1"].font = BOLD
rows = [
    # key, label, value, fmt, note
    ("price_s", "Starter plan price / month", 15, USD, "30 illustrated videos"),
    ("price_p", "Pro plan price / month", 49, USD, "150 videos, VLM check"),
    ("price_t", "Studio plan price / month", 199, USD, "500+ videos, team roles"),
    ("mix_s", "Customer mix: Starter", 0.6, PCT, ""),
    ("mix_p", "Customer mix: Pro", 0.3, PCT, ""),
    ("mix_t", "Customer mix: Studio", 0.1, PCT, "mix must total 100%"),
    ("vid_s", "Videos per customer / month: Starter", 20, '0', "average usage"),
    ("vid_p", "Videos per customer / month: Pro", 80, '0', ""),
    ("vid_t", "Videos per customer / month: Studio", 300, '0', ""),
    ("cr_share", "Share of customers buying credits", 0.2, PCT, "generated seconds"),
    ("cr_sec", "Credit seconds per buyer / month", 60, '0', ""),
    ("cr_price", "Credit price per generated second", 0.30, USD2, "customer price"),
    ("cr_cost", "Credit model cost per second (silent model)", 0.10, USD2, "vendor price; verify"),
    ("c_llm", "LLM cost per video (brief)", 0.01, USD2, "estimate"),
    ("c_tts", "Voice cost per video (paid TTS)", 0.02, USD2, "gTTS is free but not for a paid product"),
    ("c_render", "Render and storage per video", 0.002, USD2, "measured compute is far lower"),
    ("c_vlm", "VLM check cost per video", 0.02, USD2, "from plan, Phase 3"),
    ("vlm_month", "VLM check starts in month", 7, '0', "Pro and Studio only"),
    ("pay_fee", "Payment fees (% of revenue)", 0.03, PCT, "estimate; check provider"),
    ("host_fix", "Hosting fixed / month", 300, USD, "server, database, storage tools"),
    ("host_cust", "Hosting variable / customer / month", 0.10, USD2, ""),
    ("churn", "Monthly churn", 0.05, PCT, ""),
    ("team", "Engineering team / month", 6000, USD, "2 part-time engineers (assumption)"),
    ("product", "Product and support / month", 1500, USD, "0.5 FTE"),
    ("mktg", "Marketing / month", 1000, USD, "creator communities, ads"),
    ("admin", "Admin, legal, accounting / month", 500, USD, "Vietnam company costs"),
]
REF = {}
A["A3"], A["B3"], A["C3"], A["D3"] = "Item", "", "Value", "Note"
for c in "ABCD":
    A[f"{c}3"].font = BOLD
    A[f"{c}3"].fill = HEAD
for i, (key, label, value, fmt, note) in enumerate(rows, start=4):
    A[f"A{i}"] = label
    A[f"C{i}"] = value
    A[f"C{i}"].number_format = fmt
    A[f"C{i}"].font = BLUE
    A[f"D{i}"] = note
    REF[key] = f"Assumptions!$C${i}"
check_row = 4 + len(rows)
A[f"A{check_row}"] = "Check: customer mix total"
A[f"C{check_row}"] = f"={REF['mix_s']}+{REF['mix_p']}+{REF['mix_t']}"
A[f"C{check_row}"].number_format = PCT
A.column_dimensions["A"].width = 46
A.column_dimensions["C"].width = 14
A.column_dimensions["D"].width = 46

# ---------------- Unit economics ----------------
U = wb.create_sheet("Unit economics")
U["A1"] = "Unit economics per paying customer per month"
U["A1"].font = BOLD
ue = [
    ("arpu_sub", "Subscription revenue", f"={REF['mix_s']}*{REF['price_s']}+{REF['mix_p']}*{REF['price_p']}+{REF['mix_t']}*{REF['price_t']}", USD2),
    ("arpu_cr", "Credit revenue", f"={REF['cr_share']}*{REF['cr_sec']}*{REF['cr_price']}", USD2),
    ("rev", "Total revenue", "=B3+B4", USD2),
    ("vids", "Videos per customer", f"={REF['mix_s']}*{REF['vid_s']}+{REF['mix_p']}*{REF['vid_p']}+{REF['mix_t']}*{REF['vid_t']}", '0.0'),
    ("vlm_vids", "Videos per customer that get VLM check", f"={REF['mix_p']}*{REF['vid_p']}+{REF['mix_t']}*{REF['vid_t']}", '0.0'),
    ("c_prod", "Cost: video production (LLM, voice, render)", f"=B6*({REF['c_llm']}+{REF['c_tts']}+{REF['c_render']})", USD2),
    ("c_vlm", "Cost: VLM check (from month 7)", f"=B7*{REF['c_vlm']}", USD2),
    ("c_cr", "Cost: generated credits (model fees)", f"={REF['cr_share']}*{REF['cr_sec']}*{REF['cr_cost']}", USD2),
    ("c_pay", "Cost: payment fees", f"=B5*{REF['pay_fee']}", USD2),
    ("c_host", "Cost: hosting (variable)", f"={REF['host_cust']}", USD2),
    ("contrib", "Contribution per customer (after VLM check)", "=B5-B8-B9-B10-B11-B12", USD2),
    ("gm", "Gross margin % (after VLM check)", "=IF(B5=0,0,B13/B5)", PCT),
    ("fixed", "Fixed costs / month", f"={REF['team']}+{REF['product']}+{REF['mktg']}+{REF['admin']}+{REF['host_fix']}", USD),
    ("be", "Break-even paying customers (after VLM check)", "=IF(B13<=0,\"never\",ROUNDUP(B15/B13,0))", '0'),
]
for i, (key, label, formula, fmt) in enumerate(ue, start=3):
    U[f"A{i}"] = label
    U[f"B{i}"] = formula
    U[f"B{i}"].number_format = fmt
    REF["ue_" + key] = f"'Unit economics'!$B${i}"
U.column_dimensions["A"].width = 50
U.column_dimensions["B"].width = 14

# ---------------- P&L ----------------
P = wb.create_sheet("P&L (24 months)")
P["A1"] = "Monthly P&L (USD). Operating result before tax; no capex or depreciation modelled."
P["A1"].font = BOLD
P.column_dimensions["A"].width = 40
first_col = 3  # column C = month 1
last_col_letter = get_column_letter(first_col + MONTHS - 1)

def col(m):  # month index 1..MONTHS -> column letter
    return get_column_letter(first_col + m - 1)

labels = {
    3: "Month",
    4: "New customers (input)",
    5: "Churned customers",
    6: "Ending paying customers",
    8: "REVENUE",
    9: "Subscriptions",
    10: "Generated credits",
    11: "Total revenue",
    13: "COST OF REVENUE",
    14: "Video production (LLM, voice, render)",
    15: "VLM check",
    16: "Generated credits (model fees)",
    17: "Payment fees",
    18: "Hosting",
    19: "Total cost of revenue",
    20: "Gross profit",
    21: "Gross margin %",
    23: "OPERATING EXPENSES",
    24: "Engineering team",
    25: "Product and support",
    26: "Marketing",
    27: "Admin, legal, accounting",
    28: "Total operating expenses",
    30: "Operating result (EBIT, before tax)",
    31: "Cumulative operating result",
}
for r, t in labels.items():
    P[f"A{r}"] = t
    if t.isupper() or r in (11, 19, 20, 28, 30):
        P[f"A{r}"].font = BOLD

new_ramp = [10, 10, 15, 15, 20, 20, 25, 25, 30, 30, 35, 35] + [40] * 12
for m in range(1, MONTHS + 1):
    c, p = col(m), (col(m - 1) if m > 1 else None)
    P[f"{c}3"] = m
    P[f"{c}3"].font = BOLD
    P[f"{c}4"] = new_ramp[m - 1]
    P[f"{c}4"].font = BLUE
    P[f"{c}5"] = f"={p}6*{REF['churn']}" if p else 0
    P[f"{c}6"] = f"={p}6+{c}4-{c}5" if p else f"={c}4-{c}5"
    P[f"{c}9"] = f"={c}6*{REF['ue_arpu_sub']}"
    P[f"{c}10"] = f"={c}6*{REF['ue_arpu_cr']}"
    P[f"{c}11"] = f"={c}9+{c}10"
    P[f"{c}14"] = f"={c}6*{REF['ue_c_prod']}"
    P[f"{c}15"] = f"=IF({c}3>={REF['vlm_month']},{c}6*{REF['ue_c_vlm']},0)"
    P[f"{c}16"] = f"={c}6*{REF['ue_c_cr']}"
    P[f"{c}17"] = f"={c}11*{REF['pay_fee']}"
    P[f"{c}18"] = f"={REF['host_fix']}+{c}6*{REF['host_cust']}"
    P[f"{c}19"] = f"=SUM({c}14:{c}18)"
    P[f"{c}20"] = f"={c}11-{c}19"
    P[f"{c}21"] = f"=IF({c}11=0,0,{c}20/{c}11)"
    P[f"{c}24"] = f"={REF['team']}"
    P[f"{c}25"] = f"={REF['product']}"
    P[f"{c}26"] = f"={REF['mktg']}"
    P[f"{c}27"] = f"={REF['admin']}"
    P[f"{c}28"] = f"=SUM({c}24:{c}27)"
    P[f"{c}30"] = f"={c}20-{c}28"
    P[f"{c}31"] = f"={p}31+{c}30" if p else f"={c}30"
    for r in range(4, 32):
        if r == 21:
            P[f"{c}{r}"].number_format = PCT
        elif r in (3, 4, 5, 6):
            P[f"{c}{r}"].number_format = '#,##0.0' if r == 5 else '#,##0'
        elif P[f"{c}{r}"].value is not None:
            P[f"{c}{r}"].number_format = USD
    P.column_dimensions[c].width = 11

# Summary block under the P&L
P["A33"] = "Summary"
P["A33"].font = BOLD
P["A34"] = "First month with positive operating result"
P["C34"] = (f"=IFERROR(INDEX($C$3:${last_col_letter}$3,MATCH(TRUE,INDEX($C$30:${last_col_letter}$30>0,0),0)),"
            f"\"not within {MONTHS} months\")")
P["A35"] = "Operating result, year 1 (months 1-12)"
P["C35"] = f"=SUM(C30:{col(12)}30)"
P["C35"].number_format = USD
P["A36"] = "Operating result, year 2 (months 13-24)"
P["C36"] = f"=SUM({col(13)}30:{last_col_letter}30)"
P["C36"].number_format = USD
P["A37"] = "Ending customers, month 24"
P["C37"] = f"={last_col_letter}6"
P["C37"].number_format = '#,##0'
P.freeze_panes = "C4"

wb.save(OUT)
print("saved", OUT)
