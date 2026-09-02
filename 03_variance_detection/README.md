# Budget vs. Actual Variance Detection

Flags cost centers running significantly over or under budget and rolls the
results up to profit center / department level so a reviewer knows where to
look first — instead of scanning every line of a budget-vs-actual report by
eye.

## Business problem

Every close and every forecast cycle, finance has to explain why actuals
diverged from budget. With dozens of cost centers and expense categories,
manually scanning for the lines that matter doesn't scale, and it's easy to
bury a 60% overrun in a sea of lines that are within a few percent of plan.

## What this script does

`variance_detection.py`:

1. Joins budget and actuals by cost center and account category.
2. Computes dollar and percentage variance for every line.
3. Flags any line past a configurable threshold (default **15%**) as an
   overrun or underspend.
4. Rolls flagged variance up by profit center so leadership sees the
   business-level story, not just line items.
5. Exports a CSV report and a horizontal bar chart (`top_variances.png`) of
   the ten largest variances by dollar impact — ready to drop into a deck or
   dashboard.

## Run it

```bash
python variance_detection.py
```

Optional flags:

```bash
python variance_detection.py --threshold 0.10 --data-dir ../data
```

## Sample output

```
  Lines reviewed : 30
  Lines flagged  : 12
  Net variance   : $150,934.04

  Top variances requiring review:
    [   Overrun] Rates - Risk & Analytics     Facilities      budget $84,843  actual $139,956  (+65.0%)
    [   Overrun] IT & Infrastructure          Facilities      budget $56,474  actual $91,811   (+62.6%)
    ...
```

Full CSV report and chart are in [`sample_output/`](./sample_output).

## How this maps to real-world FI/CO work

This is the automation layer behind variance commentary and management
reporting — the same shape of analysis used for cost center reviews,
forecast-to-actual tracking, and the kind of scenario/sensitivity work
listed under Financial Modeling. In production this would run against
actuals pulled from CO-PA / cost center reports instead of a CSV, on a
scheduled monthly job.
