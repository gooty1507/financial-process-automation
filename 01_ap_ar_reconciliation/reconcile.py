"""
reconcile.py -- AP / AR sub-ledger to GL reconciliation.

Mirrors the reconciliation work described in the resume this project supports:
"Drove reconciliation process improvements, reducing cycle time by 18%" and
"Validated GL account mappings and reconciled AP/AR sub-ledgers against the
general ledger, reducing discrepancies and supporting a smoother month-end
close."

What it does
------------
1. Loads the AP sub-ledger, AR sub-ledger, and GL transactions into an
   in-memory SQLite database (a small, self-contained stand-in for the
   SQL-driven data pipelines described on the resume).
2. Runs SQL joins to find three categories of discrepancy for each
   sub-ledger:
     a. Invoices present in the sub-ledger with NO matching GL posting
        ("unposted").
     b. GL postings that reference an invoice_id that doesn't exist in the
        sub-ledger ("orphaned GL entry").
     c. Invoices that match but where the sub-ledger amount and GL amount
        disagree ("amount mismatch"), beyond a small rounding tolerance.
3. Writes a discrepancy report (CSV) per sub-ledger plus a combined summary,
   and prints a plain-English summary to the console.

Usage
-----
    python reconcile.py
    python reconcile.py --data-dir ../data --output-dir ./sample_output --tolerance 0.01
"""

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent


def load_data(data_dir: Path):
    ap = pd.read_csv(data_dir / "ap_subledger.csv")
    ar = pd.read_csv(data_dir / "ar_subledger.csv")
    gl = pd.read_csv(data_dir / "gl_transactions.csv")
    return ap, ar, gl


def build_db(ap: pd.DataFrame, ar: pd.DataFrame, gl: pd.DataFrame) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    ap.to_sql("ap_subledger", conn, index=False)
    ar.to_sql("ar_subledger", conn, index=False)
    gl.to_sql("gl_transactions", conn, index=False)
    return conn


def reconcile_subledger(conn: sqlite3.Connection, table: str, doc_type: str, tolerance: float) -> pd.DataFrame:
    """Return a tidy discrepancy report for one sub-ledger (AP or AR)."""

    unposted_sql = f"""
        SELECT s.invoice_id, s.amount AS subledger_amount, NULL AS gl_amount,
               'Unposted (no GL entry found)' AS discrepancy_type
        FROM {table} s
        LEFT JOIN gl_transactions g
          ON g.reference_id = s.invoice_id AND g.document_type = ?
        WHERE g.transaction_id IS NULL
    """

    orphaned_sql = f"""
        SELECT g.reference_id AS invoice_id, NULL AS subledger_amount, g.amount AS gl_amount,
               'Orphaned GL entry (no sub-ledger invoice)' AS discrepancy_type
        FROM gl_transactions g
        LEFT JOIN {table} s
          ON s.invoice_id = g.reference_id
        WHERE g.document_type = ? AND s.invoice_id IS NULL
    """

    mismatch_sql = f"""
        SELECT s.invoice_id, s.amount AS subledger_amount, g.amount AS gl_amount,
               'Amount mismatch' AS discrepancy_type
        FROM {table} s
        JOIN gl_transactions g
          ON g.reference_id = s.invoice_id AND g.document_type = ?
        WHERE ABS(s.amount - g.amount) > ?
    """

    unposted = pd.read_sql_query(unposted_sql, conn, params=(doc_type,))
    orphaned = pd.read_sql_query(orphaned_sql, conn, params=(doc_type,))
    mismatch = pd.read_sql_query(mismatch_sql, conn, params=(doc_type, tolerance))

    report = pd.concat([unposted, orphaned, mismatch], ignore_index=True)
    report["variance"] = (report["subledger_amount"].fillna(0) - report["gl_amount"].fillna(0)).round(2)
    return report


def main():
    parser = argparse.ArgumentParser(description="Reconcile AP/AR sub-ledgers against GL postings.")
    parser.add_argument("--data-dir", default=str(HERE.parent / "data"), help="Folder with the CSV inputs")
    parser.add_argument("--output-dir", default=str(HERE / "sample_output"), help="Folder to write reports to")
    parser.add_argument("--tolerance", type=float, default=0.01, help="Dollar tolerance before flagging an amount mismatch")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ap, ar, gl = load_data(data_dir)
    conn = build_db(ap, ar, gl)

    ap_report = reconcile_subledger(conn, "ap_subledger", "AP Invoice", args.tolerance)
    ar_report = reconcile_subledger(conn, "ar_subledger", "AR Invoice", args.tolerance)

    ap_report.to_csv(output_dir / "ap_discrepancies.csv", index=False)
    ar_report.to_csv(output_dir / "ar_discrepancies.csv", index=False)

    # --- Console summary -----------------------------------------------
    def summarize(name, sub_df, report_df):
        total_invoices = len(sub_df)
        total_flagged = len(report_df)
        clean_pct = 100 * (1 - total_flagged / total_invoices) if total_invoices else 100
        dollars_at_risk = report_df["variance"].abs().sum()
        print(f"\n{name} RECONCILIATION")
        print(f"  Invoices reviewed      : {total_invoices}")
        print(f"  Discrepancies flagged  : {total_flagged}  ({clean_pct:.1f}% clean)")
        print(f"  Dollar variance at risk: ${dollars_at_risk:,.2f}")
        if total_flagged:
            print("  Breakdown by type:")
            for dtype, count in report_df["discrepancy_type"].value_counts().items():
                print(f"    - {dtype}: {count}")

    print("=" * 60)
    print("AP / AR TO GENERAL LEDGER RECONCILIATION")
    print("=" * 60)
    summarize("AP", ap, ap_report)
    summarize("AR", ar, ar_report)

    print(f"\nDetailed reports written to: {output_dir}")
    print("  - ap_discrepancies.csv")
    print("  - ar_discrepancies.csv")


if __name__ == "__main__":
    main()
