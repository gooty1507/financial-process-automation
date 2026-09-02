"""
generate_data.py

Generates fully SYNTHETIC financial data that mimics the shape of data you'd
pull out of SAP FI/CO (GL, AP/AR sub-ledgers, cost/profit center budgets and
actuals). Nothing here is real company data -- it's randomly generated with a
fixed seed so results are reproducible, and it intentionally seeds a handful
of discrepancies (unposted entries, mismatched invoices, budget overruns) so
the three automation scripts in this repo have something real to catch.

Run this once before using any of the three sub-projects:

    python data/generate_data.py

Outputs CSVs into this data/ folder:
    chart_of_accounts.csv
    cost_centers.csv
    profit_centers.csv
    gl_transactions.csv
    ap_subledger.csv
    ar_subledger.csv
    budget.csv
    actuals.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date

SEED = 42
rng = np.random.default_rng(SEED)
OUT_DIR = Path(__file__).parent

PERIOD = "2026-07"  # the "month" this dataset represents

# ---------------------------------------------------------------------------
# Reference data: Chart of Accounts, Cost Centers, Profit Centers
# ---------------------------------------------------------------------------

chart_of_accounts = pd.DataFrame([
    {"account_id": "100000", "account_name": "Cash",                  "account_type": "Asset",     "normal_balance": "Debit"},
    {"account_id": "120000", "account_name": "Accounts Receivable",   "account_type": "Asset",     "normal_balance": "Debit"},
    {"account_id": "150000", "account_name": "Fixed Assets",          "account_type": "Asset",     "normal_balance": "Debit"},
    {"account_id": "200000", "account_name": "Accounts Payable",      "account_type": "Liability", "normal_balance": "Credit"},
    {"account_id": "210000", "account_name": "Accrued Liabilities",   "account_type": "Liability", "normal_balance": "Credit"},
    {"account_id": "300000", "account_name": "Retained Earnings",     "account_type": "Equity",    "normal_balance": "Credit"},
    {"account_id": "400000", "account_name": "Product Revenue",       "account_type": "Revenue",   "normal_balance": "Credit"},
    {"account_id": "410000", "account_name": "Service Revenue",       "account_type": "Revenue",   "normal_balance": "Credit"},
    {"account_id": "500000", "account_name": "COGS",                  "account_type": "Expense",   "normal_balance": "Debit"},
    {"account_id": "600000", "account_name": "Salaries & Wages",      "account_type": "Expense",   "normal_balance": "Debit"},
    {"account_id": "610000", "account_name": "Travel & Entertainment","account_type": "Expense",   "normal_balance": "Debit"},
    {"account_id": "620000", "account_name": "Software & IT",         "account_type": "Expense",   "normal_balance": "Debit"},
    {"account_id": "630000", "account_name": "Professional Services", "account_type": "Expense",   "normal_balance": "Debit"},
    {"account_id": "640000", "account_name": "Facilities",            "account_type": "Expense",   "normal_balance": "Debit"},
])

profit_centers = pd.DataFrame([
    {"profit_center_id": "PC-100", "profit_center_name": "Trading Desk - Rates"},
    {"profit_center_id": "PC-200", "profit_center_name": "Trading Desk - FX"},
    {"profit_center_id": "PC-300", "profit_center_name": "Corporate / Shared Services"},
])

cost_centers = pd.DataFrame([
    {"cost_center_id": "CC-1001", "cost_center_name": "Rates - Trading Ops",     "department": "Trading",     "profit_center_id": "PC-100"},
    {"cost_center_id": "CC-1002", "cost_center_name": "Rates - Risk & Analytics","department": "Risk",        "profit_center_id": "PC-100"},
    {"cost_center_id": "CC-2001", "cost_center_name": "FX - Trading Ops",        "department": "Trading",     "profit_center_id": "PC-200"},
    {"cost_center_id": "CC-2002", "cost_center_name": "FX - Sales Support",      "department": "Sales",       "profit_center_id": "PC-200"},
    {"cost_center_id": "CC-3001", "cost_center_name": "Finance & Accounting",    "department": "Finance",     "profit_center_id": "PC-300"},
    {"cost_center_id": "CC-3002", "cost_center_name": "IT & Infrastructure",     "department": "IT",          "profit_center_id": "PC-300"},
])

# ---------------------------------------------------------------------------
# AP sub-ledger (vendor invoices)
# ---------------------------------------------------------------------------

VENDORS = [
    ("V-001", "Meridian Office Supplies"), ("V-002", "Northstar Consulting"),
    ("V-003", "BlueWave Software Inc."),   ("V-004", "Apex Facilities Group"),
    ("V-005", "Crestline Data Services"),
]

N_AP = 60
ap_rows = []
for i in range(N_AP):
    vendor_id, vendor_name = VENDORS[rng.integers(0, len(VENDORS))]
    invoice_id = f"AP-{2000 + i}"
    invoice_date = date(2026, 7, int(rng.integers(1, 28)))
    amount = round(float(rng.uniform(500, 45000)), 2)
    ap_rows.append({
        "invoice_id": invoice_id,
        "vendor_id": vendor_id,
        "vendor_name": vendor_name,
        "invoice_date": invoice_date.isoformat(),
        "amount": amount,
        "gl_reference": invoice_id,   # will be broken for a few rows below
        "status": "Open",
    })
ap_subledger = pd.DataFrame(ap_rows)

# ---------------------------------------------------------------------------
# AR sub-ledger (customer invoices)
# ---------------------------------------------------------------------------

CUSTOMERS = [
    ("C-001", "Harborview Capital"), ("C-002", "Silverline Partners"),
    ("C-003", "Union Peak Advisors"), ("C-004", "Delta Bridge Holdings"),
]

N_AR = 45
ar_rows = []
for i in range(N_AR):
    customer_id, customer_name = CUSTOMERS[rng.integers(0, len(CUSTOMERS))]
    invoice_id = f"AR-{3000 + i}"
    invoice_date = date(2026, 7, int(rng.integers(1, 28)))
    amount = round(float(rng.uniform(2000, 120000)), 2)
    ar_rows.append({
        "invoice_id": invoice_id,
        "customer_id": customer_id,
        "customer_name": customer_name,
        "invoice_date": invoice_date.isoformat(),
        "amount": amount,
        "gl_reference": invoice_id,
        "status": "Open",
    })
ar_subledger = pd.DataFrame(ar_rows)

# ---------------------------------------------------------------------------
# GL transactions -- one posting per AP/AR invoice, plus general JEs.
# We intentionally corrupt a handful of rows to create real discrepancies.
# ---------------------------------------------------------------------------

gl_rows = []
txn_counter = 1

def next_txn_id():
    global txn_counter
    tid = f"GL-{10000 + txn_counter}"
    txn_counter += 1
    return tid

# AP postings (debit to expense, credit to AP) -- normal case
for _, inv in ap_subledger.iterrows():
    cc = cost_centers.sample(1, random_state=int(rng.integers(0, 1_000_000))).iloc[0]
    acct = chart_of_accounts[chart_of_accounts.account_type == "Expense"].sample(
        1, random_state=int(rng.integers(0, 1_000_000))
    ).iloc[0]
    gl_rows.append({
        "transaction_id": next_txn_id(),
        "posting_date": inv.invoice_date,
        "account_id": acct.account_id,
        "cost_center_id": cc.cost_center_id,
        "profit_center_id": cc.profit_center_id,
        "document_type": "AP Invoice",
        "reference_id": inv.invoice_id,
        "amount": inv.amount,
        "debit_credit": "Debit",
        "status": "Posted",
    })

# AR postings (debit AR, credit revenue) -- normal case
for _, inv in ar_subledger.iterrows():
    cc = cost_centers.sample(1, random_state=int(rng.integers(0, 1_000_000))).iloc[0]
    acct = chart_of_accounts[chart_of_accounts.account_type == "Revenue"].sample(
        1, random_state=int(rng.integers(0, 1_000_000))
    ).iloc[0]
    gl_rows.append({
        "transaction_id": next_txn_id(),
        "posting_date": inv.invoice_date,
        "account_id": acct.account_id,
        "cost_center_id": cc.cost_center_id,
        "profit_center_id": cc.profit_center_id,
        "document_type": "AR Invoice",
        "reference_id": inv.invoice_id,
        "amount": inv.amount,
        "debit_credit": "Credit",
        "status": "Posted",
    })

# A few general journal entries with no sub-ledger reference at all
for i in range(10):
    cc = cost_centers.sample(1, random_state=int(rng.integers(0, 1_000_000))).iloc[0]
    acct = chart_of_accounts.sample(1, random_state=int(rng.integers(0, 1_000_000))).iloc[0]
    gl_rows.append({
        "transaction_id": next_txn_id(),
        "posting_date": date(2026, 7, int(rng.integers(1, 28))).isoformat(),
        "account_id": acct.account_id,
        "cost_center_id": cc.cost_center_id,
        "profit_center_id": cc.profit_center_id,
        "document_type": "Journal Entry",
        "reference_id": f"JE-{9000 + i}",
        "amount": round(float(rng.uniform(200, 8000)), 2),
        "debit_credit": rng.choice(["Debit", "Credit"]),
        "status": "Posted",
    })

gl_transactions = pd.DataFrame(gl_rows)

# --- Seed intentional discrepancies -----------------------------------------

# 1) A few AP invoices with NO matching GL posting at all (simulates an
#    invoice booked in the sub-ledger but never posted to the GL).
missing_ap_idx = ap_subledger.sample(4, random_state=1).index
missing_ap_refs = set(ap_subledger.loc[missing_ap_idx, "invoice_id"])
gl_transactions = gl_transactions[
    ~((gl_transactions.document_type == "AP Invoice") & (gl_transactions.reference_id.isin(missing_ap_refs)))
].reset_index(drop=True)

# 2) A few AP invoices where the GL amount doesn't match the sub-ledger
#    (simulates a posting error / partial payment mismatch).
mismatch_ap_idx = ap_subledger.drop(index=missing_ap_idx).sample(3, random_state=2).index
mismatch_ap_refs = set(ap_subledger.loc[mismatch_ap_idx, "invoice_id"])
mask = (gl_transactions.document_type == "AP Invoice") & (gl_transactions.reference_id.isin(mismatch_ap_refs))
gl_transactions.loc[mask, "amount"] = (gl_transactions.loc[mask, "amount"] * rng.uniform(0.8, 0.95, size=mask.sum())).round(2)

# 3) A few AR invoices with no matching GL posting (unbilled / unposted revenue).
missing_ar_idx = ar_subledger.sample(3, random_state=3).index
missing_ar_refs = set(ar_subledger.loc[missing_ar_idx, "invoice_id"])
gl_transactions = gl_transactions[
    ~((gl_transactions.document_type == "AR Invoice") & (gl_transactions.reference_id.isin(missing_ar_refs)))
].reset_index(drop=True)

# 4) A handful of GL entries left in "Unposted" / "Suspense" status for the
#    month-end close checks to catch.
suspense_idx = gl_transactions.sample(6, random_state=4).index
gl_transactions.loc[suspense_idx, "status"] = rng.choice(["Unposted", "Suspense"], size=len(suspense_idx))

# 5) A couple of GL entries with an account_id that isn't in the chart of
#    accounts (simulates a bad/deactivated GL account on a manual JE).
bad_acct_idx = gl_transactions[gl_transactions.document_type == "Journal Entry"].sample(2, random_state=5).index
gl_transactions.loc[bad_acct_idx, "account_id"] = "999999"

gl_transactions = gl_transactions.sort_values("transaction_id").reset_index(drop=True)

# ---------------------------------------------------------------------------
# Budget vs. Actuals by cost center + account category (for variance detection)
# ---------------------------------------------------------------------------

EXPENSE_CATEGORIES = ["Salaries & Wages", "Travel & Entertainment", "Software & IT",
                       "Professional Services", "Facilities"]

budget_rows = []
for _, cc in cost_centers.iterrows():
    for cat in EXPENSE_CATEGORIES:
        budget_rows.append({
            "cost_center_id": cc.cost_center_id,
            "period": PERIOD,
            "account_category": cat,
            "budget_amount": round(float(rng.uniform(15000, 90000)), 2),
        })
budget = pd.DataFrame(budget_rows)

actual_rows = []
for _, row in budget.iterrows():
    # Most cost centers land close to budget; a few blow well past it.
    if rng.random() < 0.18:
        factor = rng.uniform(1.20, 1.65)   # overrun outlier
    elif rng.random() < 0.10:
        factor = rng.uniform(0.55, 0.75)   # significant underspend
    else:
        factor = rng.uniform(0.90, 1.10)   # normal variance
    actual_rows.append({
        "cost_center_id": row.cost_center_id,
        "period": row.period,
        "account_category": row.account_category,
        "actual_amount": round(row.budget_amount * factor, 2),
    })
actuals = pd.DataFrame(actual_rows)

# ---------------------------------------------------------------------------
# Write everything out
# ---------------------------------------------------------------------------

chart_of_accounts.to_csv(OUT_DIR / "chart_of_accounts.csv", index=False)
cost_centers.to_csv(OUT_DIR / "cost_centers.csv", index=False)
profit_centers.to_csv(OUT_DIR / "profit_centers.csv", index=False)
gl_transactions.to_csv(OUT_DIR / "gl_transactions.csv", index=False)
ap_subledger.to_csv(OUT_DIR / "ap_subledger.csv", index=False)
ar_subledger.to_csv(OUT_DIR / "ar_subledger.csv", index=False)
budget.to_csv(OUT_DIR / "budget.csv", index=False)
actuals.to_csv(OUT_DIR / "actuals.csv", index=False)

print("Synthetic data generated in:", OUT_DIR)
print(f"  chart_of_accounts.csv : {len(chart_of_accounts)} rows")
print(f"  cost_centers.csv      : {len(cost_centers)} rows")
print(f"  profit_centers.csv    : {len(profit_centers)} rows")
print(f"  gl_transactions.csv   : {len(gl_transactions)} rows")
print(f"  ap_subledger.csv      : {len(ap_subledger)} rows")
print(f"  ar_subledger.csv      : {len(ar_subledger)} rows")
print(f"  budget.csv            : {len(budget)} rows")
print(f"  actuals.csv           : {len(actuals)} rows")
