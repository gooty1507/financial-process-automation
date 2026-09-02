# AP / AR to GL Reconciliation

Automates the reconciliation of Accounts Payable and Accounts Receivable
sub-ledgers against General Ledger postings — the same check a finance team
runs every close to make sure sub-ledger and GL balances agree before the
books are locked.

## Business problem

In any FI/CO environment (SAP or otherwise), the AP/AR sub-ledgers and the
GL are supposed to always agree. In practice they drift apart because of
timing differences, failed postings, or manual entry errors — invoices that
never made it to the GL, GL entries with no invoice behind them, and
invoices where the amount posted doesn't match what's in the sub-ledger.
Finding these by hand in a spreadsheet is slow and error-prone at any real
transaction volume.

## What this script does

`reconcile.py` loads the AP sub-ledger, AR sub-ledger, and GL transactions
into an in-memory SQLite database and runs SQL joins to detect three
discrepancy types per sub-ledger:

| Discrepancy type | Meaning |
|---|---|
| Unposted | Invoice exists in the sub-ledger but has no matching GL posting |
| Orphaned GL entry | GL posting references an invoice that doesn't exist in the sub-ledger |
| Amount mismatch | Invoice and GL posting both exist, but the dollar amounts disagree |

It outputs a discrepancy report per sub-ledger and a console summary with
the dollar amount at risk — the number a controller actually cares about.

## Run it

```bash
python reconcile.py
```

Optional flags:

```bash
python reconcile.py --data-dir ../data --output-dir ./sample_output --tolerance 0.01
```

## Sample output

```
AP RECONCILIATION
  Invoices reviewed      : 60
  Discrepancies flagged  : 7  (88.3% clean)
  Dollar variance at risk: $101,128.75
  Breakdown by type:
    - Unposted (no GL entry found): 4
    - Amount mismatch: 3
```

Full CSV output is in [`sample_output/`](./sample_output).

## How this maps to real-world FI/CO work

This is a simplified, open-data stand-in for reconciling SAP FI sub-ledgers
(AP/AR) against the GL — the same logic applies whether the source is a SAP
extract, an Oracle/NetSuite export, or a flat file. In a production setting
you'd point this at a scheduled SAP table extract (e.g. BSEG/BSIK/BSAD) or a
data warehouse table instead of a CSV, and the SQL layer barely changes.
