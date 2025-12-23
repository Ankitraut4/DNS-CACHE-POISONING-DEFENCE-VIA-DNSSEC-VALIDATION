#!/usr/bin/env python3
import subprocess

# Restore original zone
zone_content = """$TTL 300
@       IN  SOA  ns1.example.local. admin.example.local. (
                 2024111901 3600 1800 604800 300 )
@       IN  NS   ns1.example.local.
ns1     IN  A    10.0.1.10
www     IN  A    10.0.1.20
@       IN  A    10.0.1.10
"""

subprocess.run([
    "docker", "exec", "authoritative_dns",
    "sh", "-c",
    f"echo '{zone_content}' > /etc/bind/zones/example.local.zone"
], capture_output=True)

subprocess.run([
    "docker", "exec", "authoritative_dns",
    "rndc", "reload"
], capture_output=True)

print("Restored")