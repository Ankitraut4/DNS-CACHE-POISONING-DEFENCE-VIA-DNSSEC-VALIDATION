# DNS/backend/measurements/plot_results.py
"""
Generate plots from experiment CSVs produced by run_experiments.py.

Usage examples:

    python plot_results.py --unsigned unsigned_100.csv --dnssec dnssec_100.csv
    python plot_results.py --unsigned unsigned_200.csv --dnssec dnssec_200.csv --out-prefix results_200

This will create:
    <out-prefix>_success_rates.png
    <out-prefix>_duration_boxplot.png
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def load_df(path: str, expected_mode: str):
    df = pd.read_csv(path)
    if "mode" in df.columns:
        modes = set(df["mode"].unique())
        if expected_mode not in modes:
            print(f"[!] Warning: expected mode '{expected_mode}' in {path}, found: {modes}")
    return df


def compute_stats(df, label: str):
    n = len(df)
    successes = (df["outcome"] == "success").sum()
    blocked = (df["outcome"] == "blocked").sum() if "outcome" in df.columns else 0
    success_rate = 100.0 * successes / n if n > 0 else 0.0
    print(f"\n[{label}]")
    print(f"  trials        = {n}")
    print(f"  successes     = {successes}")
    print(f"  blocked       = {blocked}")
    print(f"  success_rate  = {success_rate:.2f}%")
    return {
        "n": n,
        "successes": successes,
        "blocked": blocked,
        "success_rate": success_rate,
    }


def plot_success_rates(stats_unsigned, stats_dnssec, out_path: Path):
    labels = ["No DNSSEC", "DNSSEC Validation"]
    success_rates = [stats_unsigned["success_rate"], stats_dnssec["success_rate"]]
    blocked_rates = [
        100.0 * stats_unsigned["blocked"] / stats_unsigned["n"] if stats_unsigned["n"] > 0 else 0.0,
        100.0 * stats_dnssec["blocked"] / stats_dnssec["n"] if stats_dnssec["n"] > 0 else 0.0,
    ]

    x = range(len(labels))

    plt.figure(figsize=(6, 4))
    width = 0.35

    # Two stacked bars: success + blocked
    plt.bar(x, success_rates, width, label="Successful Poison", align="center")
    plt.bar(x, blocked_rates, width, bottom=success_rates, label="Blocked by DNSSEC", align="center")

    plt.xticks(x, labels)
    plt.ylabel("Percentage of Trials (%)")
    plt.title("DNS Cache Poisoning Outcomes")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"[+] Saved success-rate plot to {out_path}")


def plot_duration_boxplot(df_unsigned, df_dnssec, out_path: Path):
    # Convert duration_sec to float
    df_unsigned = df_unsigned.copy()
    df_dnssec = df_dnssec.copy()
    df_unsigned["duration_sec"] = pd.to_numeric(df_unsigned["duration_sec"], errors="coerce")
    df_dnssec["duration_sec"] = pd.to_numeric(df_dnssec["duration_sec"], errors="coerce")

    data = [
        df_unsigned["duration_sec"].dropna(),
        df_dnssec["duration_sec"].dropna(),
    ]
    labels = ["No DNSSEC", "DNSSEC Validation"]

    plt.figure(figsize=(6, 4))
    plt.boxplot(data, labels=labels, showmeans=True)
    plt.ylabel("Attack Attempt Duration (seconds)")
    plt.title("Distribution of Attack Attempt Durations")
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()
    print(f"[+] Saved duration boxplot to {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--unsigned", required=True, help="CSV from run_experiments.py in unsigned mode")
    ap.add_argument("--dnssec", required=True, help="CSV from run_experiments.py in dnssec mode")
    ap.add_argument("--out-prefix", default="results", help="Prefix for output PNG files")
    args = ap.parse_args()

    out_prefix = Path(args.out_prefix)

    df_unsigned = load_df(args.unsigned, expected_mode="unsigned")
    df_dnssec = load_df(args.dnssec, expected_mode="dnssec")

    stats_unsigned = compute_stats(df_unsigned, "No DNSSEC")
    stats_dnssec = compute_stats(df_dnssec, "DNSSEC Validation")

    plot_success_rates(
        stats_unsigned, stats_dnssec,
        out_prefix.with_name(out_prefix.name + "_success_rates.png")
    )

    plot_duration_boxplot(
        df_unsigned, df_dnssec,
        out_prefix.with_name(out_prefix.name + "_duration_boxplot.png")
    )


if __name__ == "__main__":
    main()
