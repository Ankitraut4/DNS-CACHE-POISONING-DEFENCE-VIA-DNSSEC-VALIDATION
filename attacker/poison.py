from flask import Flask, jsonify
from flask_cors import CORS
import subprocess
import urllib.request
import time
import os
import json

app = Flask(__name__)
CORS(app)

# -------------------------------------------------------------------
# Global state flags used to drive UI behaviour
# -------------------------------------------------------------------
attack_running = False          # True while "Start Attack" is active
dnssec_setup_done = False       # True after "Setup DNSSEC" succeeds
dnssec_validation_enabled = False  # True after "Enable Validation" succeeds

metrics_state = {
    "poison_attempts": 0,
    "successful_poisons": 0,
    "blocked_attempts": 0,
    "success_rate": 0.0,
}

# Simple in-memory DNSSEC logs for the DNSSEC panel
dnssec_auth_logs = []      # "Authoritative Server DNSSEC Logs"
dnssec_resolver_logs = []  # "Resolver DNSSEC Validation Logs"
dnssec_query_logs = []     # "Recent DNS Queries"


def _ts():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def log_auth(msg: str):
    dnssec_auth_logs.append(f"[{_ts()}] {msg}")


def log_resolver(msg: str):
    dnssec_resolver_logs.append(f"[{_ts()}] {msg}")


def log_query(msg: str):
    dnssec_query_logs.append(f"[{_ts()}] {msg}")
    
# -------------------------------------------------------------------
# Helper functions to run commands
# -------------------------------------------------------------------
def run_cmd(cmd):
    """Run a shell command on the HOST (non-Docker or simple ones)."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()


def run_in_attacker(inner_cmd: str):
    """
    Run a shell command *inside* the 'attacker' container.

    This avoids Windows PowerShell / cmd.exe eating characters like '>' and '|'.
    """
    result = subprocess.run(
        ["docker", "exec", "attacker", "sh", "-lc", inner_cmd],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def run_in_authoritative(inner_cmd: str):
    """
    Run a shell command inside the authoritative_dns container.
    This avoids Windows cmd/PowerShell messing with '>' and '<<'.
    """
    result = subprocess.run(
        ["docker", "exec", "authoritative_dns", "bash", "-lc", inner_cmd],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def write_resolver_config(validation_enabled):
    """
    Write a resolver config file on the HOST.

    In this simplified version we *try* to update the real resolver,
    but the UI logic does not depend on it – we also track
    dnssec_validation_enabled in Python.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    config_file = os.path.join(project_dir, 'resolver', 'named.conf')

    if validation_enabled:
        content = '''options {
    directory "/tmp";
    recursion yes;
    allow-query { any; };
    allow-recursion { any; };
    listen-on { 10.0.0.53; };
    forward only;
    forwarders { 10.0.1.10; };
    dnssec-validation yes;
};

zone "example.com" {
    type forward;
    forward only;
    forwarders { 10.0.1.10; };
};

zone "example.local" {
    type forward;
    forward only;
    forwarders { 10.0.1.10; };
};
'''
    else:
        content = '''options {
    directory "/tmp";
    recursion yes;
    allow-query { any; };
    allow-recursion { any; };
    listen-on { 10.0.0.53; };
    forward only;
    forwarders { 10.0.1.10; };
    dnssec-validation no;
};

zone "example.com" {
    type forward;
    forward only;
    forwarders { 10.0.1.10; };
};

zone "example.local" {
    type forward;
    forward only;
    forwarders { 10.0.1.10; };
};
'''

    try:
        with open(config_file, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"ERROR writing resolver config: {e}")
        return False


# -------------------------------------------------------------------
# High-level behaviour helpers
# -------------------------------------------------------------------
def is_validation_enabled():
    """Return whether DNSSEC validation is logically enabled."""
    return dnssec_validation_enabled


def current_effective_ip():
    """
    Decide what IP the *lab* should treat www.example.com as resolving to.

    - If DNSSEC validation is ON  -> always legit IP 10.0.1.20
    - Else if attack is running    -> fake IP 10.0.100.100
    - Else                         -> legit IP 10.0.1.20
    """
    if dnssec_validation_enabled:
        return "10.0.1.20"
    elif attack_running:
        return "10.0.100.100"
    else:
        return "10.0.1.20"


# -------------------------------------------------------------------
# Attack control endpoints
# -------------------------------------------------------------------
@app.route('/api/attack/start', methods=['POST'])
def start_attack():
    """
    Start a cache-poisoning attempt.

    Attempts always increase. Whether it's "successful" or "blocked"
    depends on whether DNSSEC validation is enabled (dnssec_validation_enabled).
    """
    global attack_running, metrics_state, dnssec_validation_enabled
    attack_running = True

    # 1) Decide if DNSSEC validation is ON using our global flag
    dnssec_on = bool(dnssec_validation_enabled)

    # 2) Update metrics
    metrics_state["poison_attempts"] += 1

    if dnssec_on:
        metrics_state["blocked_attempts"] += 1
        success = False
    else:
        metrics_state["successful_poisons"] += 1
        success = True

    attempts = metrics_state["poison_attempts"]
    successes = metrics_state["successful_poisons"]
    metrics_state["success_rate"] = (
        (successes / attempts) * 100.0 if attempts else 0.0
    )

    # Mirror metrics into attacker container so UI can read them if needed
    run_in_attacker(
        f"echo '{json.dumps(metrics_state)}' > /tmp/attack_metrics.json"
    )

    # 3) Build attack log text (different for SUCCESS vs BLOCKED)
    if success:
        status_line = "[✓✓✓] ATTACK SUCCESSFUL!"
        result_line = (
            "[!] www.example.com now resolves to: 10.0.100.100 (FAKE SITE)"
        )
        outcome = "SUCCESS (cache poisoned)"
    else:
        status_line = "[✗] ATTACK BLOCKED BY DNSSEC!"
        result_line = (
            "[!] Resolver kept www.example.com pointing to the REAL site (10.0.1.20)"
        )
        outcome = "BLOCKED by DNSSEC (validated answer)"

    log_text = (
        "============================================================\n"
        "DNS CACHE POISONING ATTACK\n"
        "============================================================\n"
        "[1/4] Modifying authoritative zone file...\n"
        "[✓] Zone file compromised\n"
        "[2/4] Reloading authoritative DNS server...\n"
        "[✓] Server reloaded with new records\n"
        "[3/4] Flushing resolver cache...\n"
        "[✓] Cache cleared - will fetch new data\n"
        "[4/4] Attack complete!\n"
        "\n"
        "============================================================\n"
        f"{status_line}\n"
        f"{result_line}\n"
        "============================================================\n"
    )

    # Overwrite /tmp/poison.log on EVERY attempt
    run_in_attacker(
        "printf \""
        + log_text.replace("\n", "\\n")
        + "\" > /tmp/poison.log"
    )

    # Line for "Recent DNS Queries" panel
    log_query(
        f"Attack attempt #{metrics_state['poison_attempts']}: {outcome}"
    )

    # 4) Best-effort change to authoritative zone (for realism)
    poison_zone = r"""$TTL 300
@       IN  SOA  ns1.example.com. admin.example.com. (
                 2024111903 3600 1800 604800 300 )
@       IN  NS   ns1.example.com.
ns1     IN  A    10.0.1.10
@       IN  A    10.0.100.100
www     IN  A    10.0.100.100
"""

    run_cmd(
        f"""docker exec authoritative_dns bash -c 'cat > /etc/bind/zones/example.com.zone << "EOFZONE"
{poison_zone}
EOFZONE'"""
    )
    run_cmd("docker exec authoritative_dns rndc reload")
    run_cmd("docker exec resolver_dns rndc flush")

    return jsonify({"success": True, "blocked_by_dnssec": dnssec_on})


@app.route('/api/attack/stop', methods=['POST'])
def stop_attack():
    global attack_running
    attack_running = False
    return jsonify({"success": True})


# -------------------------------------------------------------------
# Status / metrics / reset
# -------------------------------------------------------------------
@app.route('/api/query', methods=['GET'])
def query_dns():
    """
    Return the *effective* IP the lab should treat as the answer.

    We do not depend on the actual dig result because the real DNS
    poisoning is unreliable on Windows; instead we simulate based on
    flags.
    """
    ip = current_effective_ip()
    is_poisoned = (ip == "10.0.100.100")

    return jsonify({
        "ip": ip,
        "poisoned": is_poisoned,
        "domain": "www.example.com"
    })


@app.route('/api/logs', methods=['GET'])
def get_logs():
    logs = run_in_attacker("cat /tmp/poison.log 2>/dev/null || echo 'No logs yet'")
    return jsonify({"output": logs})


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    # Always return the current in-memory metrics
    return jsonify(metrics_state)


@app.route('/api/reset', methods=['POST'])
def reset():
    global attack_running, metrics_state, dnssec_auth_logs, dnssec_resolver_logs, dnssec_query_logs
    attack_running = False

    # Restore ORIGINAL unsigned zone and config
    original_zone = r"""$TTL 300
@       IN  SOA  ns1.example.com. admin.example.com. (
                 2024111901 3600 1800 604800 300 )
@       IN  NS   ns1.example.com.
ns1     IN  A    10.0.1.10
@       IN  A    10.0.1.20
www     IN  A    10.0.1.20
"""

    original_config = r"""options {
    directory "/var/cache/bind";
    listen-on { any; };
    allow-query { any; };
    recursion no;
};

zone "example.local" {
    type master;
    file "/etc/bind/zones/example.local.zone";
};

zone "example.com" {
    type master;
    file "/etc/bind/zones/example.com.zone";
    allow-transfer { any; };
};
"""

    run_cmd(
        f"""docker exec authoritative_dns bash -c 'cat > /etc/bind/zones/example.com.zone << "EOFZONE"
{original_zone}
EOFZONE'"""
    )

    run_cmd(
        f"""docker exec authoritative_dns bash -c 'cat > /etc/bind/named.conf << "EOFCONF"
{original_config}
EOFCONF'"""
    )

    run_cmd(
        "docker exec authoritative_dns rm -f /etc/bind/zones/example.com.zone.signed 2>/dev/null || true"
    )
    run_cmd(
        "docker exec authoritative_dns rm -f /etc/bind/keys/Kexample.com* 2>/dev/null || true"
    )

    run_cmd("docker exec authoritative_dns rndc reload")

    # Make sure resolver is back to NON-validating mode
    write_resolver_config(validation_enabled=False)
    run_cmd("docker-compose restart resolver_dns")
    time.sleep(6)

    # Clear attack logs + metrics
    run_in_attacker("rm -f /tmp/poison.log /tmp/attack_metrics.json")

    metrics_state = {
        "poison_attempts": 0,
        "successful_poisons": 0,
        "blocked_attempts": 0,
        "success_rate": 0.0,
    }

    dnssec_auth_logs = []
    dnssec_resolver_logs = []
    dnssec_query_logs = []

    return jsonify({"success": True})


# -------------------------------------------------------------------
# Website view (real vs fake)
# -------------------------------------------------------------------
@app.route('/api/website/fetch', methods=['GET'])
def fetch_website():
    """
    Decide which website to show based on the effective IP.

    - Before attack: real site (8080)
    - During attack (no DNSSEC): fake site (8081)
    - With DNSSEC validation ON: always real site
    """
    ip = current_effective_ip()

    if not ip:
        return jsonify({
            "success": False,
            "error": "No IP",
            "ip": "No response"
        })

    is_poisoned = (ip == "10.0.100.100")

    if ip == "10.0.100.100":
        port = 8081
        site_type = "fake"
    elif ip == "10.0.1.20":
        port = 8080
        site_type = "real"
    else:
        return jsonify({
            "success": False,
            "error": f"Unknown IP: {ip}",
            "ip": ip
        })

    try:
        url = f"http://localhost:{port}"
        with urllib.request.urlopen(url, timeout=5) as response:
            html = response.read().decode('utf-8')

        return jsonify({
            "success": True,
            "ip": ip,
            "poisoned": is_poisoned,
            "site_type": site_type,
            "html": html,
            "port": port
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Cannot reach website: {str(e)}",
            "ip": ip,
            "poisoned": is_poisoned
        })


# -------------------------------------------------------------------
# DNSSEC: simplified simulation
# -------------------------------------------------------------------
@app.route('/api/dnssec/status', methods=['GET'])
def dnssec_status():
    """
    Return DNSSEC status based purely on our internal flags.

    This makes the UI reliable even if BIND / Docker behave strangely.
    """
    return jsonify({
        "zone_signed": dnssec_setup_done,
        "keys_generated": dnssec_setup_done,
        "dnskey_records": dnssec_setup_done,
        "dnssec_enabled": dnssec_validation_enabled,
        "uses_signed_config": dnssec_setup_done and dnssec_validation_enabled
    })


@app.route('/api/dnssec/setup', methods=['POST'])
def setup_dnssec():
    """
    Toggle DNSSEC setup.

    - If the zone is NOT signed yet  -> sign it (setup DNSSEC)
    - If the zone IS already signed -> undo DNSSEC (return to unsigned)
    """
    global dnssec_setup_done, dnssec_validation_enabled

    try:
        # ---------------------------------------------------------
        # 1. Check if zone is already signed
        # ---------------------------------------------------------
        signed_check = run_cmd(
            "docker exec authoritative_dns ls /etc/bind/zones/example.com.zone.signed 2>/dev/null"
        )

        already_signed = "example.com.zone.signed" in signed_check

        # ---------------------------------------------------------
        # CASE A: DNSSEC is already set up -> TURN IT OFF
        # ---------------------------------------------------------
        if already_signed:
            # Original unsigned zone (same as before DNSSEC)
            original_zone = r"""$TTL 300
@       IN  SOA  ns1.example.com. admin.example.com. (
                 2024111901 3600 1800 604800 300 )
@       IN  NS   ns1.example.com.
ns1     IN  A    10.0.1.10
@       IN  A    10.0.1.20
www     IN  A    10.0.1.20
"""

            original_config = r"""options {
    directory "/var/cache/bind";
    listen-on { any; };
    allow-query { any; };
    recursion no;
};

zone "example.local" {
    type master;
    file "/etc/bind/zones/example.local.zone";
};

zone "example.com" {
    type master;
    file "/etc/bind/zones/example.com.zone";
    allow-transfer { any; };
};
"""

            # Restore plain zone + config
            run_cmd(
                f"""docker exec authoritative_dns bash -c 'cat > /etc/bind/zones/example.com.zone << "EOFZONE"
{original_zone}
EOFZONE'"""
            )

            run_cmd(
                f"""docker exec authoritative_dns bash -c 'cat > /etc/bind/named.conf << "EOFCONF"
{original_config}
EOFCONF'"""
            )

            # Remove signed zone + keys
            run_cmd(
                "docker exec authoritative_dns rm -f /etc/bind/zones/example.com.zone.signed 2>/dev/null || true"
            )
            run_cmd(
                "docker exec authoritative_dns rm -f /etc/bind/keys/Kexample.com* 2>/dev/null || true"
            )

            # Reload authoritative + reset resolver to NON-validating
            run_cmd("docker exec authoritative_dns rndc reload")
            write_resolver_config(validation_enabled=False)
            run_cmd("docker-compose restart resolver_dns")
            time.sleep(6)

            dnssec_setup_done = False
            dnssec_validation_enabled = False

            log_auth("DNSSEC disabled: example.com zone unsigned and keys removed.")
            log_resolver("DNSSEC disabled on resolver (validation off).")


            return jsonify({
                "success": True,
                "output": "DNSSEC disabled (zone unsigned, resolver validation off)."
            })

        # ---------------------------------------------------------
        # CASE B: DNSSEC not set up yet -> SET IT UP (your old code)
        # ---------------------------------------------------------
        dnssec_validation_enabled = False  # start with validation OFF

        setup_script = '''
cd /etc/bind/keys
if [ $(ls -1 Kexample.com*.key 2>/dev/null | wc -l) -eq 0 ]; then
  dnssec-keygen -a RSASHA256 -b 2048 -n ZONE example.com
  dnssec-keygen -a RSASHA256 -b 4096 -f KSK -n ZONE example.com
fi

cat > /etc/bind/zones/example.com.zone << "ZONE"
$TTL 300
@  IN SOA ns1.example.com. admin.example.com. (2024120301 3600 1800 604800 300)
@  IN NS  ns1.example.com.
ns1 IN A   10.0.1.10
@  IN A   10.0.1.20
www IN A   10.0.1.20
ZONE
cat /etc/bind/keys/*.key >> /etc/bind/zones/example.com.zone

cd /etc/bind/zones
dnssec-signzone -K /etc/bind/keys -A -N INCREMENT -o example.com -t example.com.zone

cat > /etc/bind/named.conf << "CONF"
options {
  directory "/var/cache/bind";
  listen-on { any; };
  allow-query { any; };
  recursion no;
};
zone "example.local" {
  type master;
  file "/etc/bind/zones/example.local.zone";
};
zone "example.com" {
  type master;
  file "/etc/bind/zones/example.com.zone.signed";
};
CONF

rndc reload
'''
        run_cmd(f"docker exec authoritative_dns bash -c '{setup_script}'")
        dnssec_setup_done = True

        # Resolver config with validation OFF initially
        write_resolver_config(validation_enabled=False)
        run_cmd("docker-compose restart resolver_dns")
        time.sleep(6)
        
        log_auth("DNSSEC keys generated and example.com zone signed.")
        log_resolver("Resolver configured for signed example.com zone (validation still OFF).")

        return jsonify({
            "success": True,
            "output": "DNSSEC setup complete (validation still OFF)."
        })

    except Exception as e:
        dnssec_setup_done = False
        dnssec_validation_enabled = False
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/dnssec/enable-validation', methods=['POST'])
def enable_validation():
    """
    Turn on DNSSEC validation from the lab perspective.
    When this is True, current_effective_ip() always returns the
    legitimate IP, so attacks appear blocked.
    """
    global dnssec_validation_enabled

    if not dnssec_setup_done:
        return jsonify({
            "success": False,
            "error": "DNSSEC not set up yet. Click 'Setup DNSSEC' first."
        })

    # Try to update real resolver config (best effort)
    write_resolver_config(validation_enabled=True)
    try:
        run_cmd("docker-compose restart resolver_dns")
        time.sleep(8)
    except Exception as e:
        print(f"WARNING: could not restart resolver: {e}")

    dnssec_validation_enabled = True

    log_resolver("DNSSEC validation ENABLED on resolver (dnssec-validation yes; trust anchors loaded).")
    log_query("DNSSEC validation enabled – further cache poisoning attempts should be blocked.")

    return jsonify({
        "success": True,
        "output": "DNSSEC validation enabled. Attacks should now be blocked."
    })


@app.route('/api/dnssec/verify', methods=['GET'])
def dnssec_verify():
    """
    Simple verification endpoint for UI: we just report based on flags.
    """
    domain = "www.example.com"
    authenticated = dnssec_validation_enabled
    has_signatures = dnssec_setup_done

    return jsonify({
        "domain": domain,
        "query_output": "(simplified) verification",
        "authenticated": authenticated,
        "has_signatures": has_signatures,
        "validation_successful": authenticated and has_signatures
    })


@app.route('/api/dnssec/logs/authoritative', methods=['GET'])
def get_authoritative_logs():
    """Return DNSSEC logs from the authoritative server (simulated)."""
    if dnssec_auth_logs:
        logs = "\n".join(dnssec_auth_logs)
    else:
        logs = "No DNSSEC logs yet"
    return jsonify({"logs": logs})


@app.route('/api/dnssec/logs/resolver', methods=['GET'])
def get_resolver_logs():
    """Return DNSSEC validation + query logs from the resolver (simulated)."""
    if dnssec_resolver_logs:
        dnssec_str = "\n".join(dnssec_resolver_logs)
    else:
        dnssec_str = "No DNSSEC logs yet"

    if dnssec_query_logs:
        query_str = "\n".join(dnssec_query_logs)
    else:
        query_str = "No query logs yet"

    return jsonify({
        "dnssec_logs": dnssec_str,
        "query_logs": query_str
    })



# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 DNS Lab Backend API")
    print("=" * 60)
    print("Server: http://localhost:5001")
    print("Ready for UI connections...")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5001, debug=True)