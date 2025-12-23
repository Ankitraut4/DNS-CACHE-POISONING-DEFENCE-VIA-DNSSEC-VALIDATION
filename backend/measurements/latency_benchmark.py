# DNS/backend/measurements/latency_benchmark.py
import argparse
import subprocess
import time
import statistics

def run_dig_once():
    """
    Runs dig inside the attacker container against resolver_dns.
    Returns latency in milliseconds (parsed from dig output).
    """
    cmd = [
        "docker", "exec", "attacker",
        "sh", "-lc",
        "dig +stats @resolver_dns www.example.com"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    out = result.stdout
    # dig prints lines like: ";; Query time: 3 msec"
    for line in out.splitlines():
        line = line.strip()
        if "Query time:" in line:
            parts = line.split()
            # ... Query time: 3 msec
            try:
                ms = float(parts[3])
                return ms
            except Exception:
                continue
    return None

def sample_cpu():
    """
    Very rough CPU sample using docker stats --no-stream.
    Returns string with resolver_cpu and authoritative_cpu.
    """
    cmd = [
        "docker", "stats", "--no-stream",
        "--format", "{{.Name}} {{.CPUPerc}}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    lines = result.stdout.splitlines()
    resolver_cpu = "unknown"
    auth_cpu = "unknown"
    for line in lines:
        if "resolver_dns" in line:
            resolver_cpu = line.split()[-1]
        if "authoritative_dns" in line:
            auth_cpu = line.split()[-1]
    return resolver_cpu, auth_cpu

def benchmark(n):
    latencies = []
    for i in range(1, n + 1):
        print(f"[*] Query {i}/{n}")
        t = run_dig_once()
        if t is not None:
            latencies.append(t)
            print(f"    -> {t} ms")
        else:
            print("    -> FAILED to parse latency")
        time.sleep(0.2)

    if not latencies:
        print("No successful measurements.")
        return

    print("\n[+] Latency summary (ms):")
    print(f"    count = {len(latencies)}")
    print(f"    min   = {min(latencies):.2f}")
    print(f"    max   = {max(latencies):.2f}")
    print(f"    mean  = {statistics.mean(latencies):.2f}")
    print(f"    median= {statistics.median(latencies):.2f}")

    r_cpu, a_cpu = sample_cpu()
    print("\n[+] CPU snapshot (from docker stats --no-stream):")
    print(f"    resolver_dns: {r_cpu}")
    print(f"    authoritative_dns: {a_cpu}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30, help="number of queries")
    args = ap.parse_args()

    benchmark(args.n)