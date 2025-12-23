# DNS/backend/measurements/run_experiments.py
import argparse
import csv
import time
import requests

API_BASE = "http://localhost:5001/api"

def api_get(path):
    r = requests.get(f"{API_BASE}{path}", timeout=10)
    r.raise_for_status()
    return r.json()

def api_post(path):
    r = requests.post(f"{API_BASE}{path}", timeout=20)
    r.raise_for_status()
    return r.json()

def ensure_dnssec_mode(mode: str):
    """
    mode = "unsigned"  -> DNSSEC OFF
    mode = "dnssec"    -> DNSSEC ON + validation ON
    Uses /dnssec/status, /dnssec/setup, /dnssec/enable-validation
    """
    status = api_get("/dnssec/status")

    signed = status.get("zone_signed", False)
    validation = status.get("validation_enabled", False)

    if mode == "unsigned":
        # If zone is signed, call /dnssec/setup once to UNSIGN it
        if signed:
            print("[*] Zone is signed, disabling DNSSEC...")
            api_post("/dnssec/setup")
        print("[*] Mode: UNSIGNED (DNSSEC OFF)")
        return

    if mode == "dnssec":
        # 1) Ensure zone is signed
        if not signed:
            print("[*] Zone not signed, running DNSSEC setup...")
            api_post("/dnssec/setup")
        # 2) Ensure validation is enabled
        if not validation:
            print("[*] Enabling DNSSEC validation on resolver...")
            api_post("/dnssec/enable-validation")

        print("[*] Mode: DNSSEC VALIDATION ON")

def run_trials(mode: str, trials: int, output_csv: str):
    ensure_dnssec_mode(mode)

    rows = []
    for i in range(1, trials + 1):
        print(f"[*] Trial {i}/{trials} ({mode})")

        t0 = time.perf_counter()
        resp = api_post("/attack/start")
        t1 = time.perf_counter()

        duration = t1 - t0
        blocked = resp.get("blocked_by_dnssec", False)

        outcome = "blocked" if blocked else "success"

        rows.append({
            "trial": i,
            "mode": mode,
            "blocked_by_dnssec": blocked,
            "outcome": outcome,
            "duration_sec": f"{duration:.4f}",
        })

        # tiny sleep so we don't hammer too fast
        time.sleep(0.2)

    # write CSV
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["trial", "mode", "outcome", "blocked_by_dnssec", "duration_sec"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[+] Wrote results to {output_csv}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["unsigned", "dnssec"], required=True,
                        help="unsigned (no DNSSEC) or dnssec (validation ON)")
    parser.add_argument("--trials", type=int, default=50,
                        help="number of attack trials (e.g., 50, 100, 200)")
    parser.add_argument("--out", default=None, help="output CSV path")
    args = parser.parse_args()

    if args.out is None:
        args.out = f"measurements_{args.mode}_{args.trials}.csv"

    run_trials(args.mode, args.trials, args.out)
