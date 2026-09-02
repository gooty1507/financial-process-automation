"""
close_checklist.py -- Automated month-end close validation checklist.

Mirrors the close-support work on the resume: "Configure and support SAP FI
processing... ensuring accurate financial postings" and "Coordinated UAT and
validated GL entries against business requirements, strengthening financial
controls."

What it does
------------
Runs a set of standard close-readiness checks against the GL and prints /
exports a pass-fail checklist an accountant could hand to an auditor:

  1. Unposted / suspense entries -- any GL line not in "Posted" status.
  2. Invalid GL account mappings -- GL lines posted to an account_id that
     doesn't exist in the chart of accounts.
  3. Missing cost/profit center -- GL lines missing required dimensions.
  4. Trial balance check -- total debits should equal total credits for
     posted entries.
  5. Duplicate postings -- same reference_id + document_type posted more
     than once (a common source of double-booked invoices).

Usage
-----
    python close_checklist.py
    python close_checklist.py --data-dir ../data --output-dir ./sample_output
"""

import argparse
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent


def check_unposted(gl: pd.DataFrame) -> pd.DataFrame:
    return gl[gl.status != "Posted"].copy()


def check_invalid_accounts(gl: pd.DataFrame, coa: pd.DataFrame) -> pd.DataFrame:
    valid_accounts = set(coa.account_id.astype(str))
    return gl[~gl.account_id.astype(str).isin(valid_accounts)].copy()


def check_missing_dimensions(gl: pd.DataFrame) -> pd.DataFrame:
    return gl[gl.cost_center_id.isna() | gl.profit_center_id.isna()].copy()


def check_trial_balance(gl: pd.DataFrame) -> dict:
    posted = gl[gl.status == "Posted"]
    debits = posted.loc[posted.debit_credit == "Debit", "amount"].sum()
    credits = posted.loc[posted.debit_credit == "Credit", "amount"].sum()
    return {"total_debits": round(debits, 2), "total_credits": round(credits, 2),
            "out_of_balance": round(debits - credits, 2)}


def check_duplicate_postings(gl: pd.DataFrame) -> pd.DataFrame:
    dupe_mask = gl.duplicated(subset=["reference_id", "document_type"], keep=False) & gl.reference_id.notna()
    return gl[dupe_mask].sort_values(["document_type", "reference_id"]).copy()


def main():
    parser = argparse.ArgumentParser(description="Run automated month-end close checks against the GL.")
    parser.add_argument("--data-dir", default=str(HERE.parent / "data"))
    parser.add_argument("--output-dir", default=str(HERE / "sample_output"))
    parser.add_argument("--balance-tolerance", type=float, default=0.01)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gl = pd.read_csv(data_dir / "gl_transactions.csv")
    coa = pd.read_csv(data_dir / "chart_of_accounts.csv")

    unposted = check_unposted(gl)
    bad_accounts = check_invalid_accounts(gl, coa)
    missing_dims = check_missing_dimensions(gl)
    tb = check_trial_balance(gl)
    duplicates = check_duplicate_postings(gl)

    tb_pass = abs(tb["out_of_balance"]) <= args.balance_tolerance

    checklist = pd.DataFrame([
        {"check": "No unposted / suspense GL entries", "status": "PASS" if unposted.empty else "FAIL",
         "issues_found": len(unposted)},
        {"check": "All GL postings map to a valid GL account", "status": "PASS" if bad_accounts.empty else "FAIL",
         "issues_found": len(bad_accounts)},
        {"check": "All GL postings have cost center & profit center", "status": "PASS" if missing_dims.empty else "FAIL",
         "issues_found": len(missing_dims)},
        {"check": "Trial balance (debits = credits)", "status": "PASS" if tb_pass else "FAIL",
         "issues_found": 0 if tb_pass else 1},
        {"check": "No duplicate invoice postings", "status": "PASS" if duplicates.empty else "FAIL",
         "issues_found": len(duplicates)},
    ])

    checklist.to_csv(output_dir / "close_checklist_summary.csv", index=False)
    unposted.to_csv(output_dir / "unposted_entries.csv", index=False)
    bad_accounts.to_csv(output_dir / "invalid_account_postings.csv", index=False)
    missing_dims.to_csv(output_dir / "missing_dimension_postings.csv", index=False)
    duplicates.to_csv(output_dir / "duplicate_postings.csv", index=False)

    print("=" * 60)
    print(f"MONTH-END CLOSE CHECKLIST")
    print("=" * 60)
    for _, row in checklist.iterrows():
        marker = "PASS" if row.status == "PASS" else "FAIL"
        detail = f" ({row.issues_found} issue(s))" if row.issues_found else ""
        print(f"  [{marker}] {row['check']}{detail}")

    print("\nTrial balance detail:")
    print(f"  Total debits : ${tb['total_debits']:,.2f}")
    print(f"  Total credits: ${tb['total_credits']:,.2f}")
    print(f"  Out of balance by: ${tb['out_of_balance']:,.2f}")

    n_fail = (checklist.status == "FAIL").sum()
    print(f"\n{n_fail} of {len(checklist)} checks require follow-up before close can be signed off.")
    print(f"Detailed backup written to: {output_dir}")


if __name__ == "__main__":
    main()
