#!/usr/bin/env python3
"""Find ALL hardcoded IPs, URLs, and HTTP paths in smali."""
import os
from pathlib import Path
import re

APKTOOL = Path("/tmp/apktool_out/")
found = set()

# Search all IP patterns and HTTP calls  
IP_RE = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
HTTP_RE = re.compile(r'(https?://[^"\') ]+)')

for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APKTOOL))
        if "/androidx/" in r or "/annotation/" in r: continue
        try:
            t = f.read_text("utf-8", errors="replace")
        except:
            continue
            
        ips = IP_RE.findall(t)
        for ip in ips:
            if not ip.startswith('0.') and not ip.startswith('127.') and not ip.startswith('255.'):
                if ip not in ['1.0.0.127', '1.1.1.1', '8.8.8.8', '8.8.4.4']:
                    # Find line context
                    for i, ln in enumerate(t.splitlines()):
                        if ip in ln:
                            found.add(f"  IP {ip} -> {r}:{i+1}  {ln.strip()[:120]}")
                            break
        
        urls = HTTP_RE.findall(t)
        for url in urls:
            for i, ln in enumerate(t.splitlines()):
                if url in ln:
                    found.add(f"  URL {url} -> {r}:{i+1}")
                    break

print("=== ALL HARDCODED IPs AND URLs IN SMALI ===")
for f in sorted(found):
    print(f)

import json
Path("/tmp/ip-search-results.json").write_text(
    json.dumps([{"finding": f} for f in sorted(found)], indent=2)
)
print(f"\n=== Total unique findings: {len(found)} ===")
