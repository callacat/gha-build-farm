#!/usr/bin/env python3
"""Find changzhi.top domain in smali code."""
import os
from pathlib import Path

APKTOOL = Path("/tmp/apktool_out/")

targets = ["changzhi", "sg-datahub", "47.245.87", "8.222.131"]
found = []

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
        for target in targets:
            if target in t:
                lines = t.splitlines()
                for i, ln in enumerate(lines):
                    if target in ln:
                        found.append(f"  [{target}] {r}:{i+1}  {ln.strip()[:200]}")
                        break
                break  # one hit per file

print("=== CHANGZHI.TOP IN SMALI ===")
for f in found:
    print(f)
print(f"\nTotal: {len(found)}")
if found:
    Path("/tmp/changzhi-found.txt").write_text("\n".join(found))
