#!/usr/bin/env python3
"""
Anomaly Detection Script
Analyzes logs and PCAPs for suspicious DNS activity
"""

import re
from collections import defaultdict
from datetime import datetime
import sys

def analyze_logs(log_file):
    """Scan resolver logs for anomalies"""
    print(f"[*] Analyzing log file: {log_file}")
    
    anomalies = []
    query_responses = defaultdict(list)
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                # Look for multiple responses to same query
                if 'response' in line.lower():
                    match = re.search(r'query.*?(\w+\.\w+)', line)
                    if match:
                        domain = match.group(1)
                        query_responses[domain].append(line)
    except FileNotFoundError:
        print(f"Error: File {log_file} not found")
        return []
    
    # Flag domains with multiple responses
    for domain, responses in query_responses.items():
        if len(responses) > 1:
            anomalies.append({
                'type': 'multiple_responses',
                'domain': domain,
                'count': len(responses),
                'severity': 'high'
            })
    
    return anomalies

def analyze_pcap(pcap_file):
    """Analyze PCAP for forged packets"""
    try:
        from scapy.all import rdpcap, DNS, IP
    except ImportError:
        print("Error: Scapy not installed")
        return []
    
    print(f"[*] Analyzing PCAP: {pcap_file}")
    
    try:
        packets = rdpcap(pcap_file)
    except FileNotFoundError:
        print(f"Error: File {pcap_file} not found")
        return []
    
    dns_responses = []
    
    for pkt in packets:
        if pkt.haslayer(DNS) and pkt[DNS].qr == 1:
            if pkt[DNS].ancount > 0:
                dns_responses.append({
                    'src': pkt[IP].src if pkt.haslayer(IP) else 'unknown',
                    'dst': pkt[IP].dst if pkt.haslayer(IP) else 'unknown',
                    'query': pkt[DNS].qd.qname.decode() if pkt[DNS].qd else 'unknown',
                    'answer': pkt[DNS].an.rdata if pkt[DNS].an else None
                })
    
    # Group by query
    query_groups = defaultdict(list)
    for resp in dns_responses:
        query_groups[resp['query']].append(resp)
    
    # Find duplicate responses
    anomalies = []
    for query, responses in query_groups.items():
        if len(responses) > 1:
            unique_ips = set(r['answer'] for r in responses if r['answer'])
            if len(unique_ips) > 1:
                anomalies.append({
                    'type': 'conflicting_responses',
                    'query': query,
                    'ips': list(unique_ips),
                    'severity': 'critical'
                })
    
    return anomalies

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: detector.py <log_file|pcap_file>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    if file_path.endswith('.pcap'):
        anomalies = analyze_pcap(file_path)
    else:
        anomalies = analyze_logs(file_path)
    
    print(f"\n[*] Detection Results:")
    print(f"    Found {len(anomalies)} anomalies\n")
    
    for i, anomaly in enumerate(anomalies, 1):
        print(f"[{i}] {anomaly['type'].upper()}")
        for key, value in anomaly.items():
            if key != 'type':
                print(f"    {key}: {value}")
        print()
