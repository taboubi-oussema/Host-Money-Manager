import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title='Money Manager', page_icon='💰', layout='wide')
SOURCES = ['binomty', 'la sister', 'pa', 'ather', 'Other']
ACCOUNTS = ['For Me', 'For Mom', 'Travel']
PCTS = [Decimal('0.50'), Decimal('0.05')]

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

st.title('💰 Money Manager')
st.caption('Private local prototype — do not publish without authentication.')
try:
    income_rows, expense_rows = read_data()
except Exception as exc:
    st.error('Cannot access Google Sheets. Check service account sharing, secrets, and worksheet names.')
    st.exception(exc)
    st.stop()

total_income, available = balances(income_rows, expense_rows)
cols = st.columns(5)
for col, label, val in zip(cols, ['Total Income', 'Available', 'For Me', 'For Mom', 'Travel'], [total_income, sum(available.values()), *available.values()]):
    col.metric(label, money(val))

page = st.radio('Action', ['Dashboard', 'Add Income', 'Add Expense', 'History'], horizontal=True)

if page == 'Add Income':
    with st.form('income'):
        value = st.number_input('Amount (TND)', min_value=0.01, value=10.0, step=1.0, format='%.2f')
        selected = st.selectbox('Who gave you the money?', SOURCES)
        custom = st.text_input('Custom source') if selected == 'Other' else ''
        submitted = st.form_submit_button('Review income')
    if submitted:
        source = (custom if selected == 'Other' else selected).strip()
        if not source or len(source) > 40 or source[0] in '=+-@':
            st.error('Enter a valid source (max 40 characters, no formula prefix).')
        else:
            amt = amount(value)
            me = amount(amt * PCTS[0]); mom = amount(amt * PCTS[1]); travel = amt - me - mom
            st.write(f'**Income:** {money(amt)} · **Source:** {source}')
            st.write(f'For Me {money(me)} · For Mom {money(mom)} · Travel {money(travel)}')
            st.session_state['pending_income'] = [datetime.now(ZoneInfo('Africa/Tunis')).strftime('%Y-%m-%d %H:%M'), float(amt), float(me), float(mom), float(travel), source]
    if st.session_state.get('pending_income'):
        if st.button('Confirm and save income'):
            try:
                sheets().worksheet('Data').append_row(st.session_state['pending_income'], value_input_option='RAW', table_range='A:F')
            except Exception:
                st.error('Save result uncertain. Check Google Sheets before trying again.')
            else:
                st.session_state.pop('pending_income', None)
                st.success('Income saved!'); st.rerun()

elif page == 'Add Expense':
    with st.form('expense'):
        account = st.selectbox('Account', ACCOUNTS)
        value = st.number_input('Amount (TND)', min_value=0.01, value=10.0, step=1.0, format='%.2f', key='expense_value')
        submitted = st.form_submit_button('Review expense')
    if submitted:
        amt = amount(value)
        if amt > available[account]:
            st.error(f'Insufficient balance: {money(available[account])} available.')
        else:
            st.write(f'**{account}**: {money(available[account])} → {money(available[account]-amt)}')
            st.session_state['pending_expense'] = (account, amt)
    if st.session_state.get('pending_expense'):
        if st.button('Confirm and save expense'):
            account, amt = st.session_state['pending_expense']
            try:
                inc, exp = read_data()
                _, fresh = balances(inc, exp)
                if amt > fresh[account]:
                    st.error('Balance changed. Expense not saved.')
                else:
                    sheets().worksheet('Expenses').append_row([datetime.now(ZoneInfo('Africa/Tunis')).strftime('%Y-%m-%d %H:%M'), float(amt), account], value_input_option='RAW', table_range='A:C')
                    st.session_state.pop('pending_expense', None)
                    st.success('Expense saved!'); st.rerun()
            except Exception:
                st.error('Save result uncertain. Check Google Sheets before trying again.')

elif page == 'History':
    entries = []
    for row in income_rows[1:]:
        if len(row) >= 5:
            entries.append({'Date': row[0], 'Type': 'Income', 'Amount (TND)': row[1], 'Account / Source': row[5] if len(row)>5 else ''})
    for row in expense_rows[1:]:
        if len(row) >= 3:
            entries.append({'Date': row[0], 'Type': 'Expense', 'Amount (TND)': -float(row[1]), 'Account / Source': row[2]})
    entries.sort(key=lambda r: str(r['Date']), reverse=True)
    st.dataframe(entries, use_container_width=True, hide_index=True)
else:
    st.info('Income and expenses are read live from your existing Google Sheets. Existing dashboard formulas stay in Google Sheets.')
