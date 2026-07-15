#!/usr/bin/env python3
"""Find hardcoded IP addresses in smali - modder's update server.
Target: 10.18.32.87 (private IP found in app TCP connections)"""
import re, json
from pathlib import Path

APKTOOL = Path("/tmp/apktool_out/")
OUT = "/tmp/ip-search-results.json"
findings = []
TARGET_IP = "10.18.32.87"
TARGET_PORT = 8080
TARGETS = [TARGET_IP, TARGET_PORT, "10.18.32", "8080"]

# Convert IP to various formats modders might use
ip_hex = ''.join(f'{int(x):02x}' for x in TARGET_IP.split('.'))  # 0a122057
ip_dotless = TARGET_IP.replace('.', '')
ip_hex_reversed = ''.join(f'{int(x):02x}' for x in reversed(TARGET_IP.split('.')))  # 5720120a

formats = [TARGET_IP, ip_hex, ip_dotless, ip_hex_reversed]

print(f"=== Searching for {TARGET_IP} in smali ===")
print(f"  hex: {ip_hex}")
print(f"  dotless: {ip_dotless}")
print(f"  hex_reversed: {ip_hex_reversed}")

for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APKTOOL))
        if any(x in r for x in ["/androidx/", "/annotation/", "/org/junit/"]):
            continue
        try:
            t = f.read_text("utf-8", errors="replace")
        except:
            continue
        for fmt in formats:
            if fmt in t:
                lines = t.splitlines()
                for i, ln in enumerate(lines):
                    if fmt in ln:
                        ctx_start = max(0, i-1)
                        ctx_end = min(len(lines), i+2)
                        ctx = "\n".join(lines[ctx_start:ctx_end])
                        findings.append({
                            "file": r,
                            "line": i+1,
                            "format": fmt,
                            "context": ctx.strip()[:200]
                        })
                        print(f"  [{fmt}] {r}:{i+1}")
                        break

# Also search for any .so files with this IP
print("\n=== Searching .so files ===")
for lib in sorted(APKTOOL.rglob("lib/*/*.so")):
    try:
        with open(lib, "rb") as f:
            data = f.read()
        for fmt in formats:
            if fmt.encode() in data:
                print(f"  [{fmt}] FOUND IN NATIVE: {lib}")
                findings.append({
                    "file": str(lib),
                    "type": "native_so",
                    "format": fmt
                })
                break
    except:
        pass

Path(OUT).write_text(json.dumps(findings, indent=2))
print(f"\n=== Total: {len(findings)} hits ===")
