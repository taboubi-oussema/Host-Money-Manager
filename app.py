import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
from zoneinfo import ZoneInfo
import pandas as pd
import re
from collections import defaultdict

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title='My Money Dashboard',
    page_icon='💰',
    layout='wide',
    initial_sidebar_state='collapsed'
)

# ── Constants & Theme Colors (Matching Colab Dashboard) ──────────────────────
CURRENCY = "TND"
FOR_ME_PCT, FOR_MOM_PCT, TRAVEL_PCT = Decimal('0.50'), Decimal('0.05'), Decimal('0.45')
ACCOUNTS = ['For Me', 'For Mom', 'Travel']
SOURCES = ['binomty', 'la sister', 'pa', 'Other']

# Script colors
NAVY = "#1e293b"
SLATE = "#475569"
BLUE = "#2563eb"
BLUE_L = "#dbeafe"
PINK = "#db2777"
PINK_L = "#fce7f3"
GREEN = "#059669"
GREEN_L = "#d1fae5"
TEAL = "#0d9488"
GREY_L = "#f1f5f9"

ACCOUNT_COLORS = {
    'For Me': BLUE,
    'For Mom': PINK,
    'Travel': GREEN
}
ACCOUNT_ICONS = {
    'For Me': '👤',
    'For Mom': '👩',
    'Travel': '✈️'
}

DEFAULT_SHEET_ID = '1NrxRpsZMcF8N2A6t2V9fVsbFaDko_JoOrPecewQZJO8'

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap');

html, body, [class*="css"] {{
    font-family: 'Roboto', sans-serif;
}}

#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

.block-container {{
    padding-top: 1.4rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}}

/* Main Dashboard Header Banner */
.dash-banner {{
    background: linear-gradient(135deg, {NAVY} 0%, #0f172a 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    padding: 1.35rem 1.6rem;
    text-align: center;
    color: white;
    margin-bottom: 1rem;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.28);
}}
.dash-banner h1 {{
    font-size: clamp(1.35rem, 4vw, 2.05rem);
    font-weight: 800;
    margin: 0 0 0.35rem 0;
    letter-spacing: 0.4px;
    line-height: 1.2;
}}
.dash-banner p {{
    color: #94a3b8;
    margin: 0;
    font-size: clamp(0.78rem, 2.4vw, 0.95rem);
}}

/* Header metric cards — same look as expense-section panel cards */
.top-cards-grid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 0 0 1.25rem 0;
}}
.header-metric {{
    text-align: center;
    margin-bottom: 0;
    height: 100%;
}}
.header-metric-label {{
    font-size: 0.8rem;
    color: #94a3b8;
}}
.header-metric-value {{
    font-size: 1.25rem;
    font-weight: 800;
    margin-top: 0.2rem;
    word-break: break-word;
    line-height: 1.2;
}}

@media (max-width: 960px) {{
    .top-cards-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
}}
@media (max-width: 520px) {{
    .block-container {{
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
        padding-top: 0.85rem !important;
    }}
    .dash-banner {{
        padding: 1rem 0.9rem;
        border-radius: 14px;
        margin-bottom: 0.85rem;
    }}
    .top-cards-grid {{
        grid-template-columns: 1fr;
        gap: 10px;
        margin-bottom: 1rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        padding: 8px 10px !important;
        font-size: 0.82rem;
    }}
}}

/* Section Titles (Like Colab Script bars) */
.section-banner {{
    background: {SLATE};
    color: white;
    padding: 0.6rem 1rem;
    border-radius: 8px;
    font-weight: 700;
    font-size: 1.05rem;
    letter-spacing: 0.03em;
    margin: 1.5rem 0 1rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}}

/* Card container */
.panel-box {{
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 1.2rem;
    margin-bottom: 1rem;
}}

/* Travel Goal Progress */
.goal-bar-bg {{
    background: #e2e8f0;
    border-radius: 10px;
    height: 18px;
    overflow: hidden;
    margin: 0.8rem 0;
}}
.goal-bar-fill {{
    height: 100%;
    background: {GREEN};
    border-radius: 10px;
    transition: width 0.6s ease;
}}

/* Allocation rows */
.alloc-item {{
    padding: 0.8rem 1rem;
    border-radius: 8px;
    margin-bottom: 0.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
}}

.alloc-me {{ background: {BLUE_L}; color: #1e3a8a; }}
.alloc-mom {{ background: {PINK_L}; color: #831843; }}
.alloc-travel {{ background: {GREEN_L}; color: #064e3b; }}

/* Tabs styling */
.stTabs [data-baseweb="tab-list"] {{
    gap: 8px;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
}}

/* Table toolbar: keep fullscreen only */
[data-testid="stElementToolbar"] [data-testid="stElementToolbarButton"] {{
    display: none !important;
}}
[data-testid="stElementToolbar"] [data-testid="stToolbarSeparator"],
[data-testid="stElementToolbar"] [data-testid="stElementToolbarSeparator"] {{
    display: none !important;
}}
[data-testid="stElementToolbar"] [data-testid="stElementToolbarButton"][aria-label="Fullscreen"],
[data-testid="stElementToolbar"] [data-testid="stElementToolbarButton"][title="Fullscreen"],
[data-testid="stElementToolbar"] [data-testid="stElementToolbarButton"][aria-label="View fullscreen"],
[data-testid="stElementToolbar"] [data-testid="stElementToolbarButton"][title="View fullscreen"],
[data-testid="stElementToolbar"] [data-testid="stElementToolbarButton"]:has([aria-label="Fullscreen"]),
[data-testid="stElementToolbar"] [data-testid="stElementToolbarButton"]:has([title="Fullscreen"]) {{
    display: inline-flex !important;
}}
</style>
""", unsafe_allow_html=True)


# ── Google Sheets connection ─────────────────────────────────────────────────
@st.cache_resource
def sheets():
    info = dict(st.secrets['gcp_service_account'])
    credentials = Credentials.from_service_account_info(
        info, scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    )
    sheet_key = st.secrets.get('sheet_id', DEFAULT_SHEET_ID)
    return gspread.authorize(credentials).open_by_key(sheet_key)


def clean_num_str(x):
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    s_clean = re.sub(r'[^\d.,\-]', '', s)
    if not s_clean or s_clean in ('-', '.', ',', '-.', '-,'):
        return None
    if '.' in s_clean and ',' in s_clean:
        if s_clean.rfind('.') > s_clean.rfind(','):
            s_clean = s_clean.replace(',', '')
        else:
            s_clean = s_clean.replace('.', '').replace(',', '.')
    else:
        s_clean = s_clean.replace(',', '.')
    return s_clean


def safe_float(x):
    try:
        s = clean_num_str(x)
        return float(s) if s is not None else None
    except (ValueError, TypeError):
        return None


def to_decimal(x):
    s = clean_num_str(x)
    if s is None:
        raise ValueError(f"Invalid amount: {x!r}")
    return Decimal(s).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def money(x):
    if x is None:
        return f"0.00 {CURRENCY}"
    try:
        val = Decimal(str(x))
        return f"{val:,.2f} {CURRENCY}".replace(',', ' ')
    except Exception:
        return f"{x} {CURRENCY}"


def extract_ym(date_str):
    if not date_str:
        return 'Other'
    s = str(date_str).strip()
    m = re.match(r'^(\d{4})[-/](\d{1,2})', s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    parts = re.split(r'[-/]', s.split()[0])
    if len(parts) >= 3:
        if len(parts[0]) == 4:
            return f"{parts[0]}-{int(parts[1]):02d}"
        elif len(parts[2]) == 4:
            return f"{parts[2]}-{int(parts[1]):02d}"
    return 'Other'


def load_all_data():
    sh = sheets()
    inc = sh.worksheet('Data').get('A1:F', value_render_option='UNFORMATTED_VALUE', date_time_render_option='FORMATTED_STRING')
    try:
        exp_ws = sh.worksheet('Expenses')
        exp = exp_ws.get('A1:C', value_render_option='UNFORMATTED_VALUE', date_time_render_option='FORMATTED_STRING')
        if not exp or not exp[0]:
            exp_ws.update(range_name='A1:C1', values=[['Date', 'Amount', 'Account']])
            exp = [['Date', 'Amount', 'Account']]
    except Exception:
        exp = [['Date', 'Amount', 'Account']]
    return inc, exp


# ── Load Data ────────────────────────────────────────────────────────────────
try:
    income_raw, expense_raw = load_all_data()
except Exception as exc:
    st.error('⚠️ Could not connect to Google Sheets. Verify your secrets and sheet permissions.')
    st.exception(exc)
    st.stop()


# ── Calculate Metrics exactly as Colab Script formulas ────────────────────────
total_income = Decimal('0.00')
allocated = {'For Me': Decimal('0.00'), 'For Mom': Decimal('0.00'), 'Travel': Decimal('0.00')}
spent = {'For Me': Decimal('0.00'), 'For Mom': Decimal('0.00'), 'Travel': Decimal('0.00')}
source_totals = defaultdict(Decimal)
source_counts = defaultdict(int)

# Monthly breakdown for Last 6 Months (Month -> {income, me, mom, travel, expenses})
monthly_data = defaultdict(lambda: {'income': Decimal('0'), 'For Me': Decimal('0'), 'For Mom': Decimal('0'), 'Travel': Decimal('0'), 'expenses': Decimal('0')})
history_entries = []
income_details = []

# Process Income (Data A:F)
for row in income_raw[1:]:
    if len(row) >= 2 and str(row[0]).strip():
        date_val = str(row[0]).strip()
        amt_f = safe_float(row[1])
        if amt_f is None or amt_f <= 0:
            continue
        amt_dec = to_decimal(amt_f)
        total_income += amt_dec

        # Allocations
        val_me = to_decimal(row[2]) if len(row) > 2 and safe_float(row[2]) is not None else to_decimal(amt_dec * FOR_ME_PCT)
        val_mom = to_decimal(row[3]) if len(row) > 3 and safe_float(row[3]) is not None else to_decimal(amt_dec * FOR_MOM_PCT)
        val_travel = to_decimal(row[4]) if len(row) > 4 and safe_float(row[4]) is not None else (amt_dec - val_me - val_mom)

        allocated['For Me'] += val_me
        allocated['For Mom'] += val_mom
        allocated['Travel'] += val_travel

        src = str(row[5]).strip() if len(row) > 5 and str(row[5]).strip() else 'Other'
        source_totals[src] += amt_dec
        source_counts[src] += 1

        ym = extract_ym(date_val)
        monthly_data[ym]['income'] += amt_dec
        monthly_data[ym]['For Me'] += val_me
        monthly_data[ym]['For Mom'] += val_mom
        monthly_data[ym]['Travel'] += val_travel

        history_entries.append({
            'Date': date_val,
            'Type': '🟢 Income',
            'Amount (TND)': amt_f,
            'Account / Source': src
        })
        income_details.append({
            'ym': ym,
            'Date': date_val,
            'From': src,
            'Amount': float(amt_dec),
            'For Me': float(val_me),
            'For Mom': float(val_mom),
            'Travel': float(val_travel),
        })

# Process Expenses (Expenses A:C)
for row in expense_raw[1:]:
    if len(row) >= 2 and str(row[0]).strip():
        date_val = str(row[0]).strip()
        amt_f = safe_float(row[1])
        if amt_f is None or amt_f <= 0:
            continue
        amt_dec = to_decimal(amt_f)
        acc = str(row[2]).strip() if len(row) > 2 else 'For Me'
        if acc not in spent:
            acc = 'For Me'
        spent[acc] += amt_dec

        ym = extract_ym(date_val)
        monthly_data[ym]['expenses'] += amt_dec

        history_entries.append({
            'Date': date_val,
            'Type': '🔴 Expense',
            'Amount (TND)': -amt_f,
            'Account / Source': acc
        })

available = {acc: allocated[acc] - spent[acc] for acc in ACCOUNTS}

history_entries.sort(key=lambda x: str(x['Date']), reverse=True)


# ── Banner Header (Colab rows 1-2) ───────────────────────────────────────────
st.markdown(f"""
<div class="dash-banner">
    <h1>💰 MY MONEY DASHBOARD</h1>
    <p>Currency: {CURRENCY} &nbsp;•&nbsp; Updates automatically from Google Sheets</p>
</div>
""", unsafe_allow_html=True)


# ── Top 4 Total Cards (Available Balances & Summary) ─────────────────────────
st.markdown(f"""
<div class="top-cards-grid">
    <div class="panel-box header-metric">
        <div style="font-size:1.5rem;">💰</div>
        <div class="header-metric-label">Total Income</div>
        <div class="header-metric-value" style="color:{TEAL};">{money(total_income)}</div>
    </div>
    <div class="panel-box header-metric">
        <div style="font-size:1.5rem;">👤</div>
        <div class="header-metric-label">For Me ({int(FOR_ME_PCT*100)}%) Available</div>
        <div class="header-metric-value" style="color:{BLUE};">{money(available['For Me'])}</div>
    </div>
    <div class="panel-box header-metric">
        <div style="font-size:1.5rem;">👩</div>
        <div class="header-metric-label">For Mom ({int(FOR_MOM_PCT*100)}%) Available</div>
        <div class="header-metric-value" style="color:{PINK};">{money(available['For Mom'])}</div>
    </div>
    <div class="panel-box header-metric">
        <div style="font-size:1.5rem;">✈️</div>
        <div class="header-metric-label">Travel ({int(TRAVEL_PCT*100)}%) Available</div>
        <div class="header-metric-value" style="color:{GREEN};">{money(available['Travel'])}</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Main Tabs ────────────────────────────────────────────────────────────────
tab_dash, tab_add_inc, tab_add_exp, tab_history = st.tabs([
    '📊 Full Dashboard',
    '💵 Add Income',
    '💳 Add Expense',
    '📜 History'
])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1: FULL DASHBOARD (Exact layout & sections from Colab script)
# ═════════════════════════════════════════════════════════════════════════════
with tab_dash:

    # ── Section: Where Your Money Goes (Colab rows 7-11) ─────────────────────
    st.markdown('<div class="section-banner">📊 WHERE YOUR MONEY GOES</div>', unsafe_allow_html=True)

    c_me, c_mom, c_trv = st.columns(3)
    with c_me:
        st.markdown(f"""
        <div class="alloc-item alloc-me">
            <div><strong>👤 For Me (50%)</strong><br><small>Allocated: {money(allocated['For Me'])} • Spent: {money(spent['For Me'])}</small></div>
            <div style="text-align:right;">
                <div style="font-weight:700; font-size:1.15rem;">{money(available['For Me'])}</div>
                <div style="font-size:0.75rem; opacity:0.85;">available</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c_mom:
        st.markdown(f"""
        <div class="alloc-item alloc-mom">
            <div><strong>👩 For My Mom (5%)</strong><br><small>Allocated: {money(allocated['For Mom'])} • Spent: {money(spent['For Mom'])}</small></div>
            <div style="text-align:right;">
                <div style="font-weight:700; font-size:1.15rem;">{money(available['For Mom'])}</div>
                <div style="font-size:0.75rem; opacity:0.85;">available</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c_trv:
        st.markdown(f"""
        <div class="alloc-item alloc-travel">
            <div><strong>✈️ Travel (45%)</strong><br><small>Allocated: {money(allocated['Travel'])} • Spent: {money(spent['Travel'])}</small></div>
            <div style="text-align:right;">
                <div style="font-weight:700; font-size:1.15rem;">{money(available['Travel'])}</div>
                <div style="font-size:0.75rem; opacity:0.85;">available</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


    # ── Section: Travel Goal (Colab rows 13-17) ──────────────────────────────
    st.markdown('<div class="section-banner">🎯 TRAVEL GOAL</div>', unsafe_allow_html=True)

    if 'custom_goal' not in st.session_state:
        st.session_state['custom_goal'] = 5000.0

    travel_goal_val = Decimal(str(st.session_state['custom_goal']))
    travel_saved = available['Travel']
    travel_rem = max(Decimal('0'), travel_goal_val - travel_saved)
    prog_pct = float(min(Decimal('100.0'), (travel_saved / travel_goal_val * Decimal('100.0')))) if travel_goal_val > 0 else 0.0

    st.markdown(f"""
    <div class="panel-box">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; margin-bottom:0.4rem;">
            <div style="font-size:1.15rem; font-weight:700;">✈️ Next Adventure Fund</div>
            <div style="font-size:1.2rem; font-weight:800; color:{GREEN};">{prog_pct:.1f}% Completed</div>
        </div>
        <div class="goal-bar-bg">
            <div class="goal-bar-fill" style="width: {prog_pct}%;"></div>
        </div>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap:12px; margin-top:0.8rem; text-align:center;">
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:8px;">
                <div style="font-size:0.75rem; color:#94a3b8;">Goal (edit below)</div>
                <div style="font-size:1.2rem; font-weight:700;">{money(travel_goal_val)}</div>
            </div>
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:8px;">
                <div style="font-size:0.75rem; color:#94a3b8;">Saved So Far (Available)</div>
                <div style="font-size:1.2rem; font-weight:700; color:{GREEN};">{money(travel_saved)}</div>
            </div>
            <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:8px; padding:8px;">
                <div style="font-size:0.75rem; color:#94a3b8;">Remaining to Save</div>
                <div style="font-size:1.2rem; font-weight:700; color:{PINK};">{money(travel_rem)}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander('✏️ Edit Travel Goal Target'):
        new_g = st.number_input('Goal Target (TND)', min_value=100.0, value=float(st.session_state['custom_goal']), step=250.0, format='%.2f')
        if new_g != st.session_state['custom_goal']:
            st.session_state['custom_goal'] = new_g
            st.rerun()


    # ── Section: Last 6 Months (Colab rows 19-26) ────────────────────────────
    st.markdown('<div class="section-banner">📅 LAST 6 MONTHS</div>', unsafe_allow_html=True)

    # 6 months starting from current month (Oct 2026 down to May 2026)
    today = datetime.now()
    target_months = []
    for i in range(6):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        ym_key = f"{y:04d}-{m:02d}"
        label = datetime(y, m, 1).strftime("%b %Y")  # "Oct 2026", "Sep 2026", ..., "May 2026"
        target_months.append((ym_key, label))

    m_rows = []
    chart_split = []
    for ym_key, label in target_months:
        md = monthly_data[ym_key]
        m_inc = float(md['income'])
        m_me = float(md['For Me'])
        m_mom = float(md['For Mom'])
        m_travel = float(md['Travel'])
        m_exp = float(md['expenses'])
        m_rows.append({
            'Month': label,
            'Income': m_inc,
            'For Me': m_me,
            'For Mom': m_mom,
            'Travel': m_travel,
            'Expenses': m_exp
        })
    m_df = pd.DataFrame(m_rows)
    st.dataframe(
        m_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            'Month': st.column_config.TextColumn('📅 Month'),
            'Income': st.column_config.NumberColumn('💰 Income', format='%.2f'),
            'For Me': st.column_config.NumberColumn('👤 For Me', format='%.2f'),
            'For Mom': st.column_config.NumberColumn('👩 For Mom', format='%.2f'),
            'Travel': st.column_config.NumberColumn('✈️ Travel', format='%.2f'),
            'Expenses': st.column_config.NumberColumn('🔥 Expenses', format='%.2f'),
        }
    )


    # ── Section: Who paid you this month ─────────────────────────────────────
    st.markdown('<div class="section-banner">💸 WHO PAID YOU</div>', unsafe_allow_html=True)

    month_labels = [label for _, label in target_months]
    picked_month = st.selectbox('Month', month_labels, index=0, key='who_paid_month')
    picked_ym = next(ym for ym, label in target_months if label == picked_month)

    month_incomes = [e for e in income_details if e['ym'] == picked_ym]
    month_incomes.sort(key=lambda x: str(x['Date']), reverse=True)

    if month_incomes:
        by_who = defaultdict(lambda: {'amount': 0.0, 'times': 0})
        for e in month_incomes:
            by_who[e['From']]['amount'] += e['Amount']
            by_who[e['From']]['times'] += 1
        month_total = sum(v['amount'] for v in by_who.values())
        who_rows = []
        for src, info in sorted(by_who.items(), key=lambda x: x[1]['amount'], reverse=True):
            who_rows.append({
                'From': src,
                'Amount': info['amount'],
                'Times': info['times'],
                'Share': f"{(info['amount'] / month_total * 100):.1f}%" if month_total > 0 else '0.0%',
            })
        who_rows.append({
            'From': '💰 TOTAL',
            'Amount': month_total,
            'Times': len(month_incomes),
            'Share': '100.0%',
        })
        st.dataframe(
            pd.DataFrame(who_rows),
            use_container_width=True,
            hide_index=True,
            column_config={
                'From': st.column_config.TextColumn('From'),
                'Amount': st.column_config.NumberColumn('Amount (TND)', format='%.2f'),
                'Times': st.column_config.NumberColumn('Payments'),
                'Share': st.column_config.TextColumn('Share %'),
            }
        )

        st.caption(f'Payments in {picked_month}')
        detail_df = pd.DataFrame([
            {
                'Date': e['Date'],
                'From': e['From'],
                'Amount': e['Amount'],
                'For Me': e['For Me'],
                'For Mom': e['For Mom'],
                'Travel': e['Travel'],
            }
            for e in month_incomes
        ])
        st.dataframe(
            detail_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Date': st.column_config.TextColumn('📅 Date'),
                'From': st.column_config.TextColumn('From'),
                'Amount': st.column_config.NumberColumn('💰 Amount', format='%.2f'),
                'For Me': st.column_config.NumberColumn('👤 For Me', format='%.2f'),
                'For Mom': st.column_config.NumberColumn('👩 For Mom', format='%.2f'),
                'Travel': st.column_config.NumberColumn('✈️ Travel', format='%.2f'),
            }
        )
    else:
        st.info(f'No income recorded in {picked_month}.')


    # ── Section: Income by Source (Colab rows 65-80) ─────────────────────────
    st.markdown('<div class="section-banner">💼 INCOME BY SOURCE</div>', unsafe_allow_html=True)

    src_rows = []
    for s_name, s_tot in sorted(source_totals.items(), key=lambda x: x[1], reverse=True):
        src_rows.append({
            'Source': s_name,
            'Total Received (TND)': float(s_tot),
            'Transactions': source_counts[s_name],
            'Share': f"{(float(s_tot)/float(total_income)*100):.1f}%" if total_income > 0 else '0.0%'
        })
    if src_rows:
        src_df = pd.DataFrame(src_rows)
        st.dataframe(
            src_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Source': st.column_config.TextColumn('Source'),
                'Total Received (TND)': st.column_config.NumberColumn('Total Received', format='%.2f'),
                'Transactions': st.column_config.NumberColumn('Transactions'),
                'Share': st.column_config.TextColumn('Share %'),
            }
        )
    else:
        st.info('No income sources recorded yet.')


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2: ADD INCOME
# ═════════════════════════════════════════════════════════════════════════════
with tab_add_inc:
    st.markdown('<div class="section-banner">💵 RECORD NEW INCOME</div>', unsafe_allow_html=True)

    with st.form('add_income_form', clear_on_submit=False):
        c_i1, c_i2 = st.columns(2)
        with c_i1:
            inc_amount_val = st.number_input('Amount (TND)', min_value=0.01, value=50.0, step=5.0, format='%.2f')
        with c_i2:
            inc_source_select = st.selectbox('Income Source', SOURCES)

        inc_custom_val = st.text_input('Custom Source Name') if inc_source_select == 'Other' else ''
        review_income = st.form_submit_button('🔍 Review Split (50% / 5% / 45%)', use_container_width=True, type='primary')

    if review_income:
        final_source = (inc_custom_val if inc_source_select == 'Other' else inc_source_select).strip()
        if not final_source or len(final_source) > 40 or final_source[0] in '=+-@':
            st.error('⚠️ Please enter a valid source name (max 40 chars, no formula prefix).')
        else:
            dec_amt = to_decimal(inc_amount_val)
            split_me = to_decimal(dec_amt * FOR_ME_PCT)
            split_mom = to_decimal(dec_amt * FOR_MOM_PCT)
            split_travel = dec_amt - split_me - split_mom

            st.markdown(f"""
            <div class="panel-box">
                <div style="font-weight:700; font-size:1.05rem; margin-bottom:0.8rem;">📋 Split Preview for {final_source}:</div>
                <div class="alloc-item alloc-me">
                    <span>👤 For Me (50%)</span>
                    <span>+{money(split_me)}</span>
                </div>
                <div class="alloc-item alloc-mom">
                    <span>👩 For My Mom (5%)</span>
                    <span>+{money(split_mom)}</span>
                </div>
                <div class="alloc-item alloc-travel">
                    <span>✈️ Travel Fund (45%)</span>
                    <span>+{money(split_travel)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.session_state['pending_income'] = [
                datetime.now(ZoneInfo('Africa/Tunis')).strftime('%Y-%m-%d %H:%M'),
                float(dec_amt),
                float(split_me),
                float(split_mom),
                float(split_travel),
                final_source
            ]

    if st.session_state.get('pending_income'):
        if st.button('✅ Confirm & Save Income to Google Sheets', use_container_width=True, type='primary'):
            try:
                sheets().worksheet('Data').append_row(
                    st.session_state['pending_income'],
                    value_input_option='RAW',
                    table_range='A:F'
                )
                st.session_state.pop('pending_income', None)
                st.success('🎉 Income successfully recorded and allocated!')
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f'⚠️ Error saving to Google Sheets: {e}')


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3: ADD EXPENSE
# ═════════════════════════════════════════════════════════════════════════════
with tab_add_exp:
    st.markdown('<div class="section-banner">💳 RECORD NEW EXPENSE</div>', unsafe_allow_html=True)

    # Show live available balances
    bal_cols = st.columns(3)
    for idx, acc in enumerate(ACCOUNTS):
        with bal_cols[idx]:
            icon = ACCOUNT_ICONS[acc]
            col = ACCOUNT_COLORS[acc]
            st.markdown(f"""
            <div class="panel-box" style="text-align:center;">
                <div style="font-size:1.5rem;">{icon}</div>
                <div style="font-size:0.8rem; color:#94a3b8;">{acc} Available</div>
                <div style="font-size:1.25rem; font-weight:800; color:{col}; margin-top:0.2rem;">
                    {money(available[acc])}
                </div>
            </div>
            """, unsafe_allow_html=True)

    with st.form('add_expense_form', clear_on_submit=False):
        c_e1, c_e2 = st.columns(2)
        with c_e1:
            exp_acc_choice = st.selectbox('Deduct from Account', ACCOUNTS)
        with c_e2:
            exp_val = st.number_input('Amount (TND)', min_value=0.01, value=15.0, step=5.0, format='%.2f')

        review_exp = st.form_submit_button('🔍 Review Expense', use_container_width=True, type='primary')

    if review_exp:
        dec_exp = to_decimal(exp_val)
        avail = available[exp_acc_choice]
        if dec_exp > avail:
            st.error(f"⚠️ Insufficient funds in {exp_acc_choice}: only {money(avail)} available.")
        else:
            new_bal = avail - dec_exp
            st.markdown(f"""
            <div class="panel-box">
                <div style="font-weight:700; margin-bottom:0.5rem;">Expense Confirmation — {exp_acc_choice}:</div>
                <div style="display:flex; justify-content:space-between; padding:0.5rem 0; border-bottom:1px solid rgba(255,255,255,0.08);">
                    <span>Current Balance:</span>
                    <span>{money(avail)}</span>
                </div>
                <div style="display:flex; justify-content:space-between; padding:0.5rem 0; color:#f87171; border-bottom:1px solid rgba(255,255,255,0.08);">
                    <span>− Expense:</span>
                    <span>−{money(dec_exp)}</span>
                </div>
                <div style="display:flex; justify-content:space-between; padding:0.5rem 0; font-weight:700; color:{GREEN};">
                    <span>New Balance:</span>
                    <span>{money(new_bal)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.session_state['pending_expense'] = (exp_acc_choice, dec_exp)

    if st.session_state.get('pending_expense'):
        if st.button('✅ Confirm & Save Expense', use_container_width=True, type='primary'):
            sel_acc, sel_amt = st.session_state['pending_expense']
            try:
                # Re-check live balance before recording
                fresh_inc, fresh_exp = load_all_data()
                # quick sum check
                fresh_alloc = Decimal('0.00')
                for r in fresh_inc[1:]:
                    if len(r) >= 2 and str(r[0]).strip():
                        amt_num = safe_float(r[1])
                        if amt_num:
                            d = to_decimal(amt_num)
                            if sel_acc == 'For Me':
                                fresh_alloc += to_decimal(r[2]) if len(r) > 2 and safe_float(r[2]) is not None else to_decimal(d * FOR_ME_PCT)
                            elif sel_acc == 'For Mom':
                                fresh_alloc += to_decimal(r[3]) if len(r) > 3 and safe_float(r[3]) is not None else to_decimal(d * FOR_MOM_PCT)
                            elif sel_acc == 'Travel':
                                fresh_alloc += to_decimal(r[4]) if len(r) > 4 and safe_float(r[4]) is not None else (d - to_decimal(d * FOR_ME_PCT) - to_decimal(d * FOR_MOM_PCT))

                fresh_spent = Decimal('0.00')
                for r in fresh_exp[1:]:
                    if len(r) >= 3 and str(r[0]).strip() and str(r[2]).strip() == sel_acc:
                        amt_num = safe_float(r[1])
                        if amt_num:
                            fresh_spent += to_decimal(amt_num)

                fresh_avail = fresh_alloc - fresh_spent
                if sel_amt > fresh_avail:
                    st.error('⚠️ Balance changed in Google Sheets. Expense not saved.')
                else:
                    sheets().worksheet('Expenses').append_row(
                        [
                            datetime.now(ZoneInfo('Africa/Tunis')).strftime('%Y-%m-%d %H:%M'),
                            float(sel_amt),
                            sel_acc
                        ],
                        value_input_option='RAW',
                        table_range='A:C'
                    )
                    st.session_state.pop('pending_expense', None)
                    st.success('🎉 Expense recorded successfully!')
                    st.rerun()
            except Exception as e:
                st.error(f'⚠️ Failed to save expense: {e}')


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4: HISTORY
# ═════════════════════════════════════════════════════════════════════════════
with tab_history:
    st.markdown('<div class="section-banner">📜 TRANSACTION HISTORY</div>', unsafe_allow_html=True)

    if history_entries:
        h_filter = st.selectbox('Filter Type', ['All Transactions', 'Income Only', 'Expenses Only'])

        shown = history_entries
        if h_filter == 'Income Only':
            shown = [e for e in shown if 'Income' in e['Type']]
        elif h_filter == 'Expenses Only':
            shown = [e for e in shown if 'Expense' in e['Type']]

        df_shown = pd.DataFrame(shown)
        st.dataframe(
            df_shown,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Date': st.column_config.TextColumn('📅 Date'),
                'Type': st.column_config.TextColumn('🏷️ Type'),
                'Amount (TND)': st.column_config.NumberColumn('💰 Amount (TND)', format='%.2f'),
                'Account / Source': st.column_config.TextColumn('📌 Details'),
            }
        )
        st.caption(f"Showing {len(shown)} of {len(history_entries)} records.")
    else:
        st.info('No transactions found yet.')
