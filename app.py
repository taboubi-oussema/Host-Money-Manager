import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title='Money Manager', page_icon='💰', layout='wide')

# ── Constants ────────────────────────────────────────────────────────────────
SOURCES = ['binomty', 'la sister', 'pa', 'ather', 'Other']
ACCOUNTS = ['For Me', 'For Mom', 'Travel']
PCTS = [Decimal('0.50'), Decimal('0.05')]
ACCOUNT_ICONS = {'For Me': '👤', 'For Mom': '👩', 'Travel': '✈️'}
ACCOUNT_COLORS = {'For Me': '#6C63FF', 'For Mom': '#FF6B9D', 'Travel': '#00D2FF'}

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Import Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Global ── */
.stApp {
    font-family: 'Inter', sans-serif;
}

/* ── Hide default Streamlit header/footer ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* ── Hero header ── */
.hero-header {
    text-align: center;
    padding: 1.5rem 0 1rem;
    margin-bottom: 0.5rem;
}
.hero-header h1 {
    font-size: 2.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6C63FF 0%, #00D2FF 50%, #FF6B9D 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.2rem;
    letter-spacing: -0.5px;
}
.hero-subtitle {
    color: #888;
    font-size: 0.9rem;
    font-weight: 400;
    letter-spacing: 0.5px;
}

/* ── Glassmorphism card ── */
.glass-card {
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: all 0.3s ease;
}
.glass-card:hover {
    border-color: rgba(108, 99, 255, 0.3);
    box-shadow: 0 8px 32px rgba(108, 99, 255, 0.08);
    transform: translateY(-2px);
}

/* ── Metric cards ── */
.metric-card {
    background: linear-gradient(135deg, rgba(108, 99, 255, 0.12) 0%, rgba(0, 210, 255, 0.06) 100%);
    border: 1px solid rgba(108, 99, 255, 0.15);
    border-radius: 16px;
    padding: 1.2rem 1rem;
    text-align: center;
    transition: all 0.3s ease;
}
.metric-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(108, 99, 255, 0.15);
    border-color: rgba(108, 99, 255, 0.4);
}
.metric-icon {
    font-size: 1.8rem;
    margin-bottom: 0.3rem;
}
.metric-label {
    font-size: 0.75rem;
    color: #888;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.3rem;
}
.metric-value {
    font-size: 1.35rem;
    font-weight: 700;
    color: #FAFAFA;
    letter-spacing: -0.3px;
}
.metric-value.income { color: #4ADE80; }
.metric-value.available { color: #6C63FF; }
.metric-value.forme { color: #818CF8; }
.metric-value.formom { color: #FF6B9D; }
.metric-value.travel { color: #00D2FF; }

/* ── Nav pills ── */
div[data-testid="stHorizontalBlock"] > div > div[data-testid="stRadio"] > div {
    gap: 0.5rem;
}

/* ── Tabs override with pill style ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 12px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px;
    padding: 8px 20px;
    font-weight: 500;
    font-size: 0.85rem;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #6C63FF, #5A52E0) !important;
}

/* ── Buttons ── */
.stButton > button {
    border-radius: 12px;
    font-weight: 600;
    padding: 0.6rem 2rem;
    transition: all 0.3s ease;
    border: none;
    letter-spacing: 0.3px;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(108, 99, 255, 0.3);
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6C63FF, #5A52E0);
}

/* ── Form styling ── */
.stForm {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 1.5rem;
}

/* ── Dataframe ── */
.stDataFrame {
    border-radius: 12px;
    overflow: hidden;
}

/* ── Success/Error messages ── */
.stAlert {
    border-radius: 12px;
}

/* ── Section headers ── */
.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #FAFAFA;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid rgba(108, 99, 255, 0.3);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* ── Review breakdown ── */
.breakdown-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.6rem 0.8rem;
    margin: 0.3rem 0;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 10px;
    border-left: 3px solid;
    font-size: 0.9rem;
}

/* ── Divider ── */
.fancy-divider {
    height: 1px;
    background: linear-gradient(to right, transparent, rgba(108, 99, 255, 0.3), transparent);
    margin: 1.5rem 0;
}

/* ── History badges ── */
.badge-income {
    display: inline-block;
    background: rgba(74, 222, 128, 0.15);
    color: #4ADE80;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}
.badge-expense {
    display: inline-block;
    background: rgba(248, 113, 113, 0.15);
    color: #F87171;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


# ── Google Sheets connection ─────────────────────────────────────────────────
@st.cache_resource
def sheets():
    info = dict(st.secrets['gcp_service_account'])
    credentials = Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    sh = gspread.authorize(credentials).open_by_key(st.secrets['sheet_id'])
    return sh

def amount(x):
    return Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def read_data():
    sh = sheets()
    inc = sh.worksheet('Data').get('A1:F', value_render_option='UNFORMATTED_VALUE', date_time_render_option='FORMATTED_STRING')
    exp = sh.worksheet('Expenses').get('A1:C', value_render_option='UNFORMATTED_VALUE', date_time_render_option='FORMATTED_STRING')
    return inc, exp

def balances(inc, exp):
    totals = dict.fromkeys(ACCOUNTS, Decimal('0.00'))
    income_total = Decimal('0.00')
    for r in inc[1:]:
        if len(r) >= 5:
            try:
                income_total += amount(r[1])
                for account, val in zip(ACCOUNTS, r[2:5]):
                    totals[account] += amount(val)
            except (ValueError, TypeError, ArithmeticError):
                continue
    for r in exp[1:]:
        if len(r) >= 3 and r[2] in totals:
            try:
                totals[r[2]] -= amount(r[1])
            except (ValueError, TypeError, ArithmeticError):
                continue
    return income_total, totals

def money(x):
    return f'{x:,.2f} TND'.replace(',', ' ').replace('.', ',')


# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-header">
    <h1>💰 Money Manager</h1>
    <div class="hero-subtitle">Track your income · Manage your accounts · Plan your travels</div>
</div>
""", unsafe_allow_html=True)


# ── Load data ────────────────────────────────────────────────────────────────
try:
    income_rows, expense_rows = read_data()
except Exception as exc:
    st.error('Cannot access Google Sheets. Check service account sharing, secrets, and worksheet names.')
    st.exception(exc)
    st.stop()

total_income, available = balances(income_rows, expense_rows)
total_available = sum(available.values())


# ── Dashboard Metrics ────────────────────────────────────────────────────────
metrics = [
    ('💵', 'Total Income',  money(total_income),    'income'),
    ('📊', 'Available',     money(total_available),  'available'),
    ('👤', 'For Me',        money(available['For Me']),   'forme'),
    ('👩', 'For Mom',       money(available['For Mom']),  'formom'),
    ('✈️', 'Travel',        money(available['Travel']),   'travel'),
]

cols = st.columns(5, gap='medium')
for col, (icon, label, val, css_class) in zip(cols, metrics):
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">{icon}</div>
            <div class="metric-label">{label}</div>
            <div class="metric-value {css_class}">{val}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)


# ── Navigation ───────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(['📊 Dashboard', '💵 Add Income', '💳 Add Expense', '📜 History'])


# ── Tab 1: Dashboard ─────────────────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-header">📈 Account Overview</div>', unsafe_allow_html=True)

    for acc in ACCOUNTS:
        icon = ACCOUNT_ICONS[acc]
        color = ACCOUNT_COLORS[acc]
        balance = available[acc]
        pct = (balance / total_available * 100) if total_available > 0 else Decimal('0')

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"""
            <div class="glass-card" style="padding: 1rem 1.2rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="display:flex; align-items:center; gap:0.7rem;">
                        <span style="font-size:1.5rem;">{icon}</span>
                        <div>
                            <div style="font-weight:600; font-size:1rem;">{acc}</div>
                            <div style="color:#888; font-size:0.8rem;">Balance available</div>
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-weight:700; font-size:1.2rem; color:{color};">{money(balance)}</div>
                        <div style="color:#888; font-size:0.75rem;">{pct:.1f}% of total</div>
                    </div>
                </div>
                <div style="margin-top:0.8rem; background:rgba(255,255,255,0.06); border-radius:8px; height:6px; overflow:hidden;">
                    <div style="width:{min(float(pct), 100):.1f}%; height:100%; background:linear-gradient(90deg, {color}, {color}88); border-radius:8px; transition: width 0.5s ease;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-header">💡 Quick Info</div>', unsafe_allow_html=True)

    info_col1, info_col2, info_col3 = st.columns(3)
    with info_col1:
        total_expenses = total_income - total_available
        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <div style="font-size:1.5rem;">🔥</div>
            <div class="metric-label">Total Spent</div>
            <div style="font-size:1.1rem; font-weight:600; color:#F87171;">{money(total_expenses)}</div>
        </div>
        """, unsafe_allow_html=True)
    with info_col2:
        savings_rate = (total_available / total_income * 100) if total_income > 0 else Decimal('0')
        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <div style="font-size:1.5rem;">💎</div>
            <div class="metric-label">Savings Rate</div>
            <div style="font-size:1.1rem; font-weight:600; color:#4ADE80;">{savings_rate:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with info_col3:
        n_transactions = len(income_rows[1:]) + len(expense_rows[1:])
        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <div style="font-size:1.5rem;">📝</div>
            <div class="metric-label">Transactions</div>
            <div style="font-size:1.1rem; font-weight:600; color:#818CF8;">{n_transactions}</div>
        </div>
        """, unsafe_allow_html=True)


# ── Tab 2: Add Income ────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-header">💵 Record New Income</div>', unsafe_allow_html=True)

    with st.form('income', clear_on_submit=False):
        col_a, col_b = st.columns(2)
        with col_a:
            value = st.number_input('Amount (TND)', min_value=0.01, value=10.0, step=1.0, format='%.2f')
        with col_b:
            selected = st.selectbox('Who gave you the money?', SOURCES)
        custom = st.text_input('Custom source name') if selected == 'Other' else ''
        submitted = st.form_submit_button('🔍  Review Income', use_container_width=True, type='primary')

    if submitted:
        source = (custom if selected == 'Other' else selected).strip()
        if not source or len(source) > 40 or source[0] in '=+-@':
            st.error('⚠️ Enter a valid source (max 40 characters, no formula prefix).')
        else:
            amt = amount(value)
            me = amount(amt * PCTS[0]); mom = amount(amt * PCTS[1]); travel = amt - me - mom

            st.markdown(f"""
            <div class="glass-card">
                <div style="font-weight:600; margin-bottom:0.8rem; font-size:1rem;">📋 Income Breakdown — {source}</div>
                <div class="breakdown-row" style="border-color:#4ADE80;">
                    <span>💵 Total Income</span>
                    <span style="font-weight:700; color:#4ADE80;">{money(amt)}</span>
                </div>
                <div class="breakdown-row" style="border-color:#818CF8;">
                    <span>👤 For Me (50%)</span>
                    <span style="font-weight:600; color:#818CF8;">{money(me)}</span>
                </div>
                <div class="breakdown-row" style="border-color:#FF6B9D;">
                    <span>👩 For Mom (5%)</span>
                    <span style="font-weight:600; color:#FF6B9D;">{money(mom)}</span>
                </div>
                <div class="breakdown-row" style="border-color:#00D2FF;">
                    <span>✈️ Travel (45%)</span>
                    <span style="font-weight:600; color:#00D2FF;">{money(travel)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.session_state['pending_income'] = [
                datetime.now(ZoneInfo('Africa/Tunis')).strftime('%Y-%m-%d %H:%M'),
                float(amt), float(me), float(mom), float(travel), source
            ]

    if st.session_state.get('pending_income'):
        if st.button('✅  Confirm & Save Income', use_container_width=True, type='primary'):
            try:
                sheets().worksheet('Data').append_row(
                    st.session_state['pending_income'],
                    value_input_option='RAW', table_range='A:F'
                )
            except Exception:
                st.error('⚠️ Save result uncertain. Check Google Sheets before trying again.')
            else:
                st.session_state.pop('pending_income', None)
                st.success('🎉 Income saved successfully!')
                st.balloons()
                st.rerun()


# ── Tab 3: Add Expense ───────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">💳 Record New Expense</div>', unsafe_allow_html=True)

    # Show account balances before spending
    bal_cols = st.columns(3)
    for i, acc in enumerate(ACCOUNTS):
        with bal_cols[i]:
            icon = ACCOUNT_ICONS[acc]
            color = ACCOUNT_COLORS[acc]
            st.markdown(f"""
            <div class="glass-card" style="text-align:center; padding:0.8rem;">
                <div style="font-size:1.2rem;">{icon}</div>
                <div style="font-size:0.75rem; color:#888; margin:0.2rem 0;">{acc}</div>
                <div style="font-weight:700; color:{color};">{money(available[acc])}</div>
            </div>
            """, unsafe_allow_html=True)

    with st.form('expense'):
        col_a, col_b = st.columns(2)
        with col_a:
            account = st.selectbox('Account', ACCOUNTS)
        with col_b:
            value = st.number_input('Amount (TND)', min_value=0.01, value=10.0, step=1.0, format='%.2f', key='expense_value')
        submitted = st.form_submit_button('🔍  Review Expense', use_container_width=True, type='primary')

    if submitted:
        amt = amount(value)
        if amt > available[account]:
            st.error(f'⚠️ Insufficient balance in {account}: only {money(available[account])} available.')
        else:
            new_balance = available[account] - amt
            color = ACCOUNT_COLORS[account]
            st.markdown(f"""
            <div class="glass-card">
                <div style="font-weight:600; margin-bottom:0.8rem;">📋 Expense Preview — {account}</div>
                <div class="breakdown-row" style="border-color:{color};">
                    <span>Current Balance</span>
                    <span style="font-weight:600;">{money(available[account])}</span>
                </div>
                <div class="breakdown-row" style="border-color:#F87171;">
                    <span>− Expense</span>
                    <span style="font-weight:600; color:#F87171;">−{money(amt)}</span>
                </div>
                <div class="breakdown-row" style="border-color:#4ADE80;">
                    <span>New Balance</span>
                    <span style="font-weight:700; color:#4ADE80;">{money(new_balance)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.session_state['pending_expense'] = (account, amt)

    if st.session_state.get('pending_expense'):
        if st.button('✅  Confirm & Save Expense', use_container_width=True, type='primary'):
            account, amt = st.session_state['pending_expense']
            try:
                inc, exp = read_data()
                _, fresh = balances(inc, exp)
                if amt > fresh[account]:
                    st.error('⚠️ Balance changed. Expense not saved.')
                else:
                    sheets().worksheet('Expenses').append_row(
                        [datetime.now(ZoneInfo('Africa/Tunis')).strftime('%Y-%m-%d %H:%M'), float(amt), account],
                        value_input_option='RAW', table_range='A:C'
                    )
                    st.session_state.pop('pending_expense', None)
                    st.success('🎉 Expense saved successfully!')
                    st.rerun()
            except Exception:
                st.error('⚠️ Save result uncertain. Check Google Sheets before trying again.')


# ── Tab 4: History ───────────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="section-header">📜 Transaction History</div>', unsafe_allow_html=True)

    entries = []
    for row in income_rows[1:]:
        if len(row) >= 5:
            entries.append({
                'Date': row[0],
                'Type': '🟢 Income',
                'Amount (TND)': float(row[1]),
                'Account / Source': row[5] if len(row) > 5 else ''
            })
    for row in expense_rows[1:]:
        if len(row) >= 3:
            entries.append({
                'Date': row[0],
                'Type': '🔴 Expense',
                'Amount (TND)': -float(row[1]),
                'Account / Source': row[2]
            })
    entries.sort(key=lambda r: str(r['Date']), reverse=True)

    if entries:
        df = pd.DataFrame(entries)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Date': st.column_config.TextColumn('📅 Date', width='medium'),
                'Type': st.column_config.TextColumn('Type', width='small'),
                'Amount (TND)': st.column_config.NumberColumn(
                    '💰 Amount (TND)',
                    format='%.2f',
                    width='medium',
                ),
                'Account / Source': st.column_config.TextColumn('📌 Details', width='medium'),
            }
        )
        st.caption(f'Showing {len(entries)} transaction{"s" if len(entries) != 1 else ""}')
    else:
        st.info('No transactions recorded yet. Add your first income or expense!')


# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; padding:2rem 0 1rem; color:#555; font-size:0.75rem;">
    Made with 💜 · Money Manager v1.0 · Data synced live from Google Sheets
</div>
""", unsafe_allow_html=True)
