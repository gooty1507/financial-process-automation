# Month-End Close Checklist Automation

Runs a set of standard close-readiness checks against the General Ledger and
produces a pass/fail checklist — the kind of pre-close validation that
normally eats the first two days of every close cycle.

## Business problem

Before a close can be signed off, someone has to confirm the GL is clean:
no unposted or suspense entries, no postings to invalid accounts, every line
carrying the required cost/profit center, the trial balance actually
balancing, and no duplicate invoice postings. Doing this manually in Excel
means re-running the same set of filters and pivot tables every single month.

## What this script does

`close_checklist.py` runs five checks against the GL:

1. **No unposted / suspense entries** — every GL line should be in `Posted` status.
2. **Valid GL account mappings** — every `account_id` on the GL should exist in the chart of accounts.
3. **Required dimensions present** — every line should carry a cost center and profit center.
4. **Trial balance** — total debits should equal total credits for posted entries.
5. **No duplicate postings** — the same invoice shouldn't be posted to the GL twice.

It prints a pass/fail checklist to the console and writes backup detail (the
exact rows that failed each check) so a reviewer can go straight to the
problem entries instead of re-deriving them.

## Run it

```bash
python close_checklist.py
```

Optional flags:

```bash
python close_checklist.py --data-dir ../data --output-dir ./sample_output --balance-tolerance 0.01
```

## Sample output

```
  [FAIL] No unposted / suspense GL entries (6 issue(s))
  [FAIL] All GL postings map to a valid GL account (2 issue(s))
  [PASS] All GL postings have cost center & profit center
  [FAIL] Trial balance (debits = credits)
  [PASS] No duplicate invoice postings

3 of 5 checks require follow-up before close can be signed off.
```

Full CSV backup for each failed check is in [`sample_output/`](./sample_output).

> Note: the synthetic GL data in this repo isn't a fully balanced
> double-entry ledger (it's randomly generated for demo purposes), so the
> trial balance check is expected to fail here — that's intentional, to show
> the check catching something real rather than always passing.

## How this maps to real-world FI/CO work

These are the same categories of check a functional consultant or BA builds
into close-readiness reporting — usually as a set of saved SAP queries or a
BI report run against BSEG/FAGLFLEXA extracts. Wiring this script to a real
extract instead of a CSV is a one-line change; the check logic doesn't move.
