#!/usr/bin/env python3
"""方案A: 替换 oneseeker.top 为 apitw.ldmnq.com (LDPlayer 域名，永远可连)"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
REPLACEMENT = "apitw.ldmnq.com"
TARGET = "oneseeker.top"
MODS = HITS = 0

RE_URL = r'const-string\s+([vp\d]+)\s*,\s*"(https?://[^"]*' + re.escape(TARGET) + r'[^"]*)"'
RE_BARE = r'const-string\s+([vp\d]+)\s*,\s*"([^"]*' + re.escape(TARGET) + r'[^"]*)"'

for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        if "/androidx/" in r: continue
        text = f.read_text("utf-8", errors="replace")
        if TARGET not in text: continue
        lines = text.splitlines(keepends=True)
        dirty = False
        for i, ln in enumerate(lines):
            if TARGET not in ln: continue
            m = re.search(RE_URL, ln)
            if m:
                reg = m.group(1)
                indent = re.match(r"^(\s*)", ln).group(1)
                lines[i] = f'{indent}const-string {reg}, "https://{REPLACEMENT}:443/appUpdate"  # redirected\n'
                dirty = True; HITS += 1
                print(f"  [A] {r}:{i+1}")
                break
            m2 = re.search(RE_BARE, ln)
            if m2:
                reg = m2.group(1)
                indent = re.match(r"^(\s*)", ln).group(1)
                lines[i] = f'{indent}const-string {reg}, "{REPLACEMENT}"  # redirected\n'
                dirty = True; HITS += 1
                print(f"  [A] {r}:{i+1} (bare)")
                break
        if dirty:
            f.write_text("".join(lines), encoding="utf-8")
            MODS += 1
print(f"=== 方案A Done: {MODS} files, {HITS} hits ===")
