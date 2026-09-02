"""
variance_detection.py -- Budget vs. Actual variance detection by cost center.

Mirrors the resume bullets: "Model risk-adjusted financial scenarios using
Python automation to accelerate variance detection" and "Performed gap
analysis... recommending improvements for month-end close and budgeting
cycles."

What it does
------------
1. Loads budget and actuals by cost_center_id / account_category.
2. Computes dollar and percentage variance for every line.
3. Flags outliers where the variance exceeds a threshold (default 15%),
   distinguishing overruns from underspends.
4. Rolls flagged lines up to profit center / department level so a reviewer
   can see where to focus first.
5. Writes a CSV variance report and a PNG chart of the largest variances
   (the kind of visual you'd drop straight into an executive dashboard).

Usage
-----
    python variance_detection.py
    python variance_detection.py --threshold 0.10 --data-dir ../data
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless-safe backend
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(description="Flag budget vs. actual variances by cost center.")
    parser.add_argument("--data-dir", default=str(HERE.parent / "data"))
    parser.add_argument("--output-dir", default=str(HERE / "sample_output"))
    parser.add_argument("--threshold", type=float, default=0.15, help="Variance %% (as a decimal) before a line is flagged")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    budget = pd.read_csv(data_dir / "budget.csv")
    actuals = pd.read_csv(data_dir / "actuals.csv")
    cost_centers = pd.read_csv(data_dir / "cost_centers.csv")
    profit_centers = pd.read_csv(data_dir / "profit_centers.csv")

    df = budget.merge(actuals, on=["cost_center_id", "period", "account_category"])
    df = df.merge(cost_centers, on="cost_center_id").merge(profit_centers, on="profit_center_id")

    df["variance_amount"] = (df["actual_amount"] - df["budget_amount"]).round(2)
    df["variance_pct"] = (df["variance_amount"] / df["budget_amount"]).round(4)
    df["direction"] = df["variance_amount"].apply(lambda v: "Overrun" if v > 0 else "Underspend")
    df["flagged"] = df["variance_pct"].abs() >= args.threshold

    df = df.sort_values("variance_pct", key=lambda s: s.abs(), ascending=False)

    report_cols = ["cost_center_id", "cost_center_name", "department", "profit_center_name",
                   "account_category", "budget_amount", "actual_amount",
                   "variance_amount", "variance_pct", "direction", "flagged"]
    df[report_cols].to_csv(output_dir / "variance_report.csv", index=False)

    flagged = df[df.flagged]

    # --- Console summary --------------------------------------------------
    print("=" * 60)
    print(f"BUDGET vs. ACTUAL VARIANCE DETECTION  (threshold: {args.threshold:.0%})")
    print("=" * 60)
    print(f"  Lines reviewed : {len(df)}")
    print(f"  Lines flagged  : {len(flagged)}")
    print(f"  Total budget   : ${df.budget_amount.sum():,.2f}")
    print(f"  Total actual   : ${df.actual_amount.sum():,.2f}")
    print(f"  Net variance   : ${df.variance_amount.sum():,.2f}")

    if not flagged.empty:
        print("\n  Top variances requiring review:")
        for _, row in flagged.head(8).iterrows():
            print(f"    [{row.direction:>10}] {row.cost_center_name:<28} {row.account_category:<24} "
                  f"budget ${row.budget_amount:>10,.0f}  actual ${row.actual_amount:>10,.0f}  "
                  f"({row.variance_pct:+.1%})")

        by_pc = flagged.groupby("profit_center_name")["variance_amount"].sum().sort_values(key=abs, ascending=False)
        print("\n  Net flagged variance by profit center:")
        for pc, amt in by_pc.items():
            print(f"    {pc:<32} ${amt:>12,.2f}")

    # --- Chart: top 10 variances by absolute dollar impact -----------------
    top10 = df.reindex(df.variance_amount.abs().sort_values(ascending=False).index).head(10)
    labels = top10.cost_center_name + " – " + top10.account_category
    colors = ["#c0392b" if v > 0 else "#2980b9" for v in top10.variance_amount]

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(labels[::-1], top10.variance_amount[::-1], color=colors[::-1])
    ax.set_xlabel("Variance ($) -- red = over budget, blue = under budget")
    ax.set_title("Top 10 Budget Variances by Cost Center / Category")
    ax.axvline(0, color="black", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(output_dir / "top_variances.png", dpi=150)
    plt.close(fig)

    print(f"\nDetailed report written to: {output_dir}")
    print("  - variance_report.csv")
    print("  - top_variances.png")


if __name__ == "__main__":
    main()
