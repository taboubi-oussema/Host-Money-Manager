import json
import sys
from pathlib import Path
import gspread
from gspread.utils import a1_range_to_grid_range
from google.oauth2.service_account import Credentials

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ============================================================
# 🔧 MONEY MANAGER — SCRIPT 2 of 2: DASHBOARD SETUP
#    Safe to re-run any time. Dashboard lives in columns G:N,
#    the data table (A:F) and the Expenses sheet are never modified.
#
#    Layout (all in one place):
#      rows  1-5   title + 4 total cards
#      rows  7-11  where your money goes
#      rows 13-17  travel goal (your goal in H14 is kept)
#      rows 19-26  last 6 months (income split + expenses)
#      rows 28-33  account balances (allocated / spent / available)
#      rows 35-63  4 charts
#      rows 65-80  income by source + chart
# ============================================================

SHEET_ID = "1NrxRpsZMcF8N2A6t2V9fVsbFaDko_JoOrPecewQZJO8"
CURRENCY = "TND"
DEFAULT_TRAVEL_GOAL = 5000     # only used the very first time; later your own goal is kept
FONT = "Roboto"
MAX_ROW = 5000
FOR_ME, FOR_MOM, TRAVEL = 50, 5, 45   # same as the daily script (only used for the header text)
HEADERS = ["📅 Date", "💰 Money Total", f"👤 For Me ({FOR_ME}%)",
           f"👩 For My Mom ({FOR_MOM}%)", f"✈️ Travel ({TRAVEL}%)", "💼 Income Source"]
DASH_ROWS = 120                # dashboard zone G1:N120 is rebuilt on every run

# Authenticate using local service_account.json
creds_path = Path(__file__).resolve().parent / "service_account.json"
if not creds_path.exists():
    raise FileNotFoundError(f"Cannot find service_account.json at {creds_path}")

creds = Credentials.from_service_account_file(
    str(creds_path),
    scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(creds)
spreadsheet = gc.open_by_key(SHEET_ID)

titles = [w.title for w in spreadsheet.worksheets()]
if "Data" not in titles:
    raise RuntimeError("Worksheet 'Data' not found. Aborting (it is never created automatically).")
if "Expenses" not in titles:
    w = spreadsheet.add_worksheet(title="Expenses", rows=1000, cols=3)
    w.update(range_name="A1:C1", values=[["Date", "Amount", "Account"]])
    print("🆕 Created 'Expenses' worksheet.")

data = spreadsheet.worksheet("Data")
print("✅ Connected to Google Sheet:", spreadsheet.title)


# ---------- keep the travel goal you already typed in H14 ----------
def read_existing_goal():
    try:
        row = data.batch_get(["G14:H14"], value_render_option="UNFORMATTED_VALUE")[0][0]
        if str(row[0]).startswith("Goal") and float(row[1]) > 0:
            return float(row[1])
    except Exception:
        pass
    return None


goal = read_existing_goal() or DEFAULT_TRAVEL_GOAL
print(f"🎯 Travel goal kept: {goal:,.0f} {CURRENCY}")

if data.col_count < 14:
    data.add_cols(14 - data.col_count)
if data.row_count < DASH_ROWS:
    data.add_rows(DASH_ROWS - data.row_count)

# ---------- header row A1:F1 ----------
data.update(range_name="A1:F1", values=[HEADERS])
print("✅ Header row set")


# ---------- helpers ----------
def rgb(h):
    h = h.lstrip("#")
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}


NAVY, SLATE, WHITE = "#1e293b", "#475569", "#ffffff"
BLUE, BLUE_L = "#2563eb", "#dbeafe"
PINK, PINK_L = "#db2777", "#fce7f3"
GREEN, GREEN_L = "#059669", "#d1fae5"
TEAL, GREY_L = "#0d9488", "#f1f5f9"
MONEY = f'#,##0.00 "{CURRENCY}"'


def fmt(bg=None, color=WHITE, bold=False, size=11, h="LEFT", numfmt=None):
    f = {"textFormat": {"bold": bold, "fontSize": size, "fontFamily": FONT,
                        "foregroundColor": rgb(color)},
         "horizontalAlignment": h, "verticalAlignment": "MIDDLE"}
    if bg:
        f["backgroundColor"] = rgb(bg)
    if numfmt:
        f["numberFormat"] = {"type": "NUMBER", "pattern": numfmt}
    return f


def borders(color="#94a3b8"):
    side = {"style": "SOLID", "color": rgb(color)}
    return {"borders": {"top": side, "bottom": side, "left": side, "right": side}}


def grid(a1):
    return a1_range_to_grid_range(a1, data.id)


def col_width(start, end, px):
    return {"updateDimensionProperties": {
        "range": {"sheetId": data.id, "dimension": "COLUMNS", "startIndex": start, "endIndex": end},
        "properties": {"pixelSize": px}, "fields": "pixelSize"}}


def src(r1, r2, c1, c2):
    return {"sourceRange": {"sources": [{"sheetId": data.id, "startRowIndex": r1, "endRowIndex": r2,
                                         "startColumnIndex": c1, "endColumnIndex": c2}]}}


# ---------- reset the dashboard zone (G:N only; data table A:F is never touched) ----------
print("🔄 Resetting dashboard zone G1:N" + str(DASH_ROWS) + "...")
spreadsheet.batch_update({"requests": [
    {"unmergeCells": {"range": grid(f"G1:N{DASH_ROWS}")}},
    {"repeatCell": {"range": grid(f"G1:N{DASH_ROWS}"), "cell": {}, "fields": "userEnteredFormat"}},
]})
data.batch_clear([f"G1:N{DASH_ROWS}"])

# ---------- content ----------
R = MAX_ROW
cells = {
    "G1": "💰 MY MONEY DASHBOARD",
    "G2": f"Currency: {CURRENCY}  •  Updates automatically",
    "G4": "TOTAL INCOME", "I4": "FOR ME", "K4": "FOR MY MOM", "M4": "TRAVEL FUND",
    "G5": f"=SUM(B2:B{R})", "I5": f"=SUM(C2:C{R})", "K5": f"=SUM(D2:D{R})", "M5": f"=SUM(E2:E{R})",
    "G7": "📊 WHERE YOUR MONEY GOES",
    "G8": "Category", "H8": "Amount", "I8": "Share",
    "G9": "👤 For Me", "H9": f"=SUM(C2:C{R})", "I9": "=IFERROR(H9/$G$5,0)",
    "G10": "👩 For My Mom", "H10": f"=SUM(D2:D{R})", "I10": "=IFERROR(H10/$G$5,0)",
    "G11": "✈️ Travel", "H11": f"=SUM(E2:E{R})", "I11": "=IFERROR(H11/$G$5,0)",
    "G13": "🎯 TRAVEL GOAL",
    "G14": "Goal (edit me ✏️)", "H14": goal,
    "G15": "Saved so far", "H15": "=J32",          # travel money still available (after expenses)
    "G16": "Remaining", "H16": "=MAX(H14-H15,0)",
    "G17": "Progress",
    "H17": '=SPARKLINE(MAX(0,MIN(H15/H14,1)),{"charttype","bar";"max",1;"color1","#059669";"empty","#e2e8f0"})',
    "L17": "=IFERROR(MAX(0,MIN(H15/H14,1)),0)",
    "G19": "📅 LAST 6 MONTHS",
    "G20": "Month", "H20": "Income", "I20": "For Me", "J20": "For Mom", "K20": "Travel", "L20": "Expenses",
    "G28": "💳 ACCOUNT BALANCES",
    "G29": "Account", "H29": "Allocated", "I29": "Spent", "J29": "Available",
    "G33": "TOTAL", "H33": "=SUM(H30:H32)", "I33": "=SUM(I30:I32)", "J33": "=SUM(J30:J32)",
    "G65": "💼 INCOME BY SOURCE",
}

# last 6 months: works whether dates are real dates or text like "2026-10-26 14:30"
for i in range(6):
    r = 21 + i
    cells[f"G{r}"] = f"=EDATE(DATE(YEAR(TODAY()),MONTH(TODAY()),1),{i - 5})"
    for dcol, scol in zip("HIJK", "BCDE"):
        cells[f"{dcol}{r}"] = (
            f'=SUMIFS(${scol}$2:${scol}${R},$A$2:$A${R},TEXT($G{r},"yyyy-mm")&"*")'
            f'+SUMIFS(${scol}$2:${scol}${R},$A$2:$A${R},">="&$G{r},$A$2:$A${R},"<"&EDATE($G{r},1))')
    cells[f"L{r}"] = (
        f'=SUMIFS(Expenses!$B$2:$B${R},Expenses!$A$2:$A${R},TEXT($G{r},"yyyy-mm")&"*")'
        f'+SUMIFS(Expenses!$B$2:$B${R},Expenses!$A$2:$A${R},">="&$G{r},Expenses!$A$2:$A${R},"<"&EDATE($G{r},1))')

# account balances (names must match the Expenses sheet exactly)
for i, (name, col) in enumerate([("For Me", "C"), ("For Mom", "D"), ("Travel", "E")]):
    r = 30 + i
    cells[f"G{r}"] = name
    cells[f"H{r}"] = f"=SUM({col}2:{col}{R})"
    cells[f"I{r}"] = f"=SUMIFS(Expenses!$B$2:$B${R},Expenses!$C$2:$C${R},$G{r})"
    cells[f"J{r}"] = f"=H{r}-I{r}"

# income by source: ONE formula fills the whole table, sorted by total, blanks excluded
query_text = ("select Col1, sum(Col2), count(Col1) where Col1 is not null and Col1 <> '' "
              "group by Col1 order by sum(Col2) desc "
              "label Col1 'Source', sum(Col2) 'Total Received', count(Col1) 'Transactions'")
cells["G66"] = f'=IFERROR(QUERY({{F2:F{R},B2:B{R}}},"{query_text}",0),"No sources yet")'

print("📝 Writing formulas and cells to Google Sheets...")
data.batch_update(
    [{"range": a, "values": [[v]]} for a, v in cells.items()],
    value_input_option="USER_ENTERED")

# ---------- styles (sent in ONE call) ----------
F = []   # list of {"range":..., "format":...}


def style(rng, f):
    F.append({"range": rng, "format": f})


# column F (Income Source) - same look as the other table columns
last_f = min(MAX_ROW, data.row_count)
# header row A1:F1 (colors match the dashboard cards)
for rng, c in [("A1", SLATE), ("B1", TEAL), ("C1", BLUE), ("D1", PINK), ("E1", GREEN), ("F1", NAVY)]:
    style(rng, {**fmt(c, bold=True, size=12, h="CENTER"), "wrapStrategy": "WRAP"})
style("A1:F1", borders("#ffffff"))
style(f"F2:F{last_f}", fmt(None, color="#0f172a", h="LEFT"))
style(f"F2:F{last_f}", borders())

# dashboard base + header
style(f"G1:N{DASH_ROWS}", fmt(None, color="#0f172a"))
style("G1:N1", fmt(NAVY, bold=True, size=18, h="CENTER"))
style("G2:N2", fmt(NAVY, color="#cbd5e1", size=10, h="CENTER"))
for rng, c in [("G4:H5", TEAL), ("I4:J5", BLUE), ("K4:L5", PINK), ("M4:N5", GREEN)]:
    style(rng, fmt(c, bold=True, h="CENTER"))
style("G4:N4", {"textFormat": {"fontSize": 10, "bold": True, "fontFamily": FONT,
                               "foregroundColor": rgb("#f8fafc")}})
for rng, c in [("G5:H5", TEAL), ("I5:J5", BLUE), ("K5:L5", PINK), ("M5:N5", GREEN)]:
    style(rng, {"backgroundColor": rgb(c), "numberFormat": {"type": "NUMBER", "pattern": MONEY},
                "textFormat": {"bold": True, "fontSize": 14, "fontFamily": FONT,
                               "foregroundColor": rgb(WHITE)}})

# section bars + table headers
for rng in ("G7:N7", "G13:N13", "G19:N19", "G28:N28", "G65:N65"):
    style(rng, fmt(SLATE, bold=True, size=12))
for rng in ("G8:I8", "G20:L20", "G29:J29", "G66:I66"):
    style(rng, fmt(GREY_L, color=NAVY, bold=True, h="CENTER"))

# where your money goes
style("G9:G11", fmt(None, color="#0f172a", bold=True))
style("H9:H11", fmt(None, color="#0f172a", h="RIGHT", numfmt=MONEY))
style("I9:I11", fmt(None, color="#0f172a", h="CENTER", numfmt="0.0%"))
style("G9:I9", {"backgroundColor": rgb(BLUE_L)})
style("G10:I10", {"backgroundColor": rgb(PINK_L)})
style("G11:I11", {"backgroundColor": rgb(GREEN_L)})

# travel goal
style("G14:G17", fmt(None, color="#0f172a", bold=True))
style("H14:H16", fmt(None, color="#0f172a", h="RIGHT", numfmt=MONEY))
style("H14", {"backgroundColor": rgb("#fef9c3"), "textFormat": {
    "bold": True, "fontSize": 11, "fontFamily": FONT}})
style("L17", fmt(None, color=GREEN, bold=True, size=12, h="CENTER", numfmt="0%"))

# last 6 months
style("G21:G26", {"numberFormat": {"type": "DATE", "pattern": "mmm yyyy"},
                  "textFormat": {"bold": True, "fontFamily": FONT, "fontSize": 11},
                  "horizontalAlignment": "LEFT"})
style("H21:L26", fmt(None, color="#0f172a", h="RIGHT", numfmt=MONEY))

# account balances
style("G30:G32", fmt(None, color="#0f172a", bold=True))
style("H30:J33", fmt(None, color="#0f172a", h="RIGHT", numfmt=MONEY))
style("G33:J33", fmt(GREY_L, color=NAVY, bold=True))
style("H33:J33", fmt(GREY_L, color=NAVY, bold=True, h="RIGHT", numfmt=MONEY))

# income by source table body (room for up to 10 sources)
style("G67:G76", fmt(None, color="#0f172a", bold=True))
style("H67:H76", fmt(None, color="#0f172a", h="RIGHT", numfmt=MONEY))
style("I67:I76", fmt(None, color="#0f172a", h="CENTER", numfmt="0"))

for rng in ("G4:N5", "G8:I11", "G14:H17", "G20:L26", "G29:J33", "G66:I76"):
    style(rng, borders())

print("🎨 Applying formatting and styles...")
data.batch_format(F)

# ---------- merges, column widths, charts ----------
OWN_CHARTS = {"Where your money goes", "Monthly income split", "Income by source",
              "Balances (allocated / spent / available)", "Expenses by account"}

meta = spreadsheet.fetch_sheet_metadata()
reqs = []
for s in meta["sheets"]:
    if s["properties"]["sheetId"] == data.id:
        for ch in s.get("charts", []):
            title = ch.get("spec", {}).get("title", "") or ""
            if title in OWN_CHARTS or title.startswith("MM4:"):
                reqs.append({"deleteEmbeddedObject": {"objectId": ch["chartId"]}})

for rng in ["G1:N1", "G2:N2", "G4:H4", "I4:J4", "K4:L4", "M4:N4",
            "G5:H5", "I5:J5", "K5:L5", "M5:N5",
            "G7:N7", "G13:N13", "G19:N19", "G28:N28", "G65:N65", "H17:K17"]:
    reqs.append({"mergeCells": {"range": grid(rng), "mergeType": "MERGE_ALL"}})


def anchor(row, col, w, h):
    return {"overlayPosition": {"anchorCell": {"sheetId": data.id, "rowIndex": row, "columnIndex": col},
                                "widthPixels": w, "heightPixels": h}}


reqs += [
    # row of charts 1 (starts row 35)
    {"addChart": {"chart": {
        "spec": {"title": "Where your money goes",
                 "pieChart": {"legendPosition": "BOTTOM_LEGEND", "domain": src(8, 11, 6, 7),
                              "series": src(8, 11, 7, 8), "pieHole": 0.5}},
        "position": anchor(34, 6, 400, 270)}}},
    {"addChart": {"chart": {
        "spec": {"title": "Monthly income split",
                 "basicChart": {"chartType": "COLUMN", "legendPosition": "BOTTOM_LEGEND",
                                "stackedType": "STACKED",
                                "axis": [{"position": "BOTTOM_AXIS"}, {"position": "LEFT_AXIS"}],
                                "domains": [{"domain": src(20, 26, 6, 7)}],
                                "series": [
                                    {"series": src(20, 26, 8, 9), "targetAxis": "LEFT_AXIS",
                                     "colorStyle": {"rgbColor": rgb(BLUE)}},
                                    {"series": src(20, 26, 9, 10), "targetAxis": "LEFT_AXIS",
                                     "colorStyle": {"rgbColor": rgb(PINK)}},
                                    {"series": src(20, 26, 10, 11), "targetAxis": "LEFT_AXIS",
                                     "colorStyle": {"rgbColor": rgb(GREEN)}}],
                                "headerCount": 0}},
        "position": anchor(34, 10, 420, 270)}}},
    # row of charts 2 (starts row 50)
    {"addChart": {"chart": {
        "spec": {"title": "Balances (allocated / spent / available)",
                 "basicChart": {"chartType": "COLUMN", "legendPosition": "BOTTOM_LEGEND",
                                "axis": [{"position": "BOTTOM_AXIS"}, {"position": "LEFT_AXIS"}],
                                "domains": [{"domain": src(28, 32, 6, 7)}],
                                "series": [{"series": src(28, 32, c, c + 1), "targetAxis": "LEFT_AXIS"}
                                           for c in (7, 8, 9)],
                                "headerCount": 1}},
        "position": anchor(49, 6, 400, 270)}}},
    {"addChart": {"chart": {
        "spec": {"title": "Expenses by account",
                 "pieChart": {"legendPosition": "BOTTOM_LEGEND", "domain": src(29, 32, 6, 7),
                              "series": src(29, 32, 8, 9), "pieHole": 0.5}},
        "position": anchor(49, 10, 420, 270)}}},
    # income by source (donut), to the right of the source table
    {"addChart": {"chart": {
        "spec": {"title": "Income by source",
                 "pieChart": {"legendPosition": "BOTTOM_LEGEND", "domain": src(66, 76, 6, 7),
                              "series": src(66, 76, 7, 8), "pieHole": 0.5}},
        "position": anchor(64, 9, 440, 270)}}},
    {"updateDimensionProperties": {      # header row height
        "range": {"sheetId": data.id, "dimension": "ROWS", "startIndex": 0, "endIndex": 1},
        "properties": {"pixelSize": 40}, "fields": "pixelSize"}},
    {"updateSheetProperties": {          # keep the header visible while scrolling
        "properties": {"sheetId": data.id, "gridProperties": {"frozenRowCount": 1}},
        "fields": "gridProperties.frozenRowCount"}},
    col_width(0, 5, 170),    # A..E (table columns)
    col_width(5, 6, 170),    # F  (Income Source)
    col_width(6, 7, 170),    # G
    col_width(7, 14, 112),   # H..N
]

print("📊 Applying merges, dimensions, and charts...")
spreadsheet.batch_update({"requests": reqs})
print("🎉 Done! Google Sheets Dashboard rebuilt successfully: totals, goal, 6 months, balances, charts, and income by source!")
