# Money Manager Streamlit starter

This is a **local prototype**, not yet suitable for public deployment. It has no user authentication. Do not publish until access control is added.

## Setup
1. Back up your Google Sheet.
2. In Google Cloud Console, create a project, enable the Google Sheets API, create a service account, and download its JSON key. Treat the key like a password.
3. Share the spreadsheet with the service account's `client_email` as Editor.
4. Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` and replace placeholders with JSON key fields and the **correct spreadsheet ID**. Do not commit this file.
5. Ensure the spreadsheet has worksheets named `Data` and `Expenses`, with `Expenses` columns A:C = Date, Amount, Account.
6. Install Python 3.10+ and run:
   `pip install -r requirements.txt`
   `streamlit run app.py`
7. Test read-only Dashboard and History first, then a small income/expense after checking your backup.

## Notes
- Streamlit reruns the script after actions; the app uses session state to hold a pending transaction for confirmation.
- This starter does not change existing Google Sheets dashboard formulas or number formatting.
- The `append_row` approach is for a single-user prototype, not an atomic financial ledger. For multi-user/public use, add stronger transaction IDs, locking, idempotency, and authentication.
- Service account credentials must stay on the server, never in browser code or a public repository.
