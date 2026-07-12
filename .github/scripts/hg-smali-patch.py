#!/usr/bin/env python3
"""红果短剧 v10 — 网络层拦截：毒化更新检测 URL"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
POISON_URL = "http://127.0.0.1"
KEYWORDS = r"(update|upgrade|version|check|force)"
MODS = 0
HITS = 0

for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir():
        continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        if "/androidx/" in r or "/annotation/" in r:
            continue
        t = f.read_text("utf-8", errors="replace")
        lines = t.splitlines(keepends=True)
        dirty = False

        for i, ln in enumerate(lines):
            # const-string vREG, "http://...update..."
            m = re.search(
                r'const-string\s+([vp\d]+)\s*,\s*"(https?://[^"]*' + KEYWORDS + r'[^"]*)"',
                ln,
                re.IGNORECASE,
            )
            if not m:
                continue
            reg = m.group(1)
            url = m.group(2)
            indent = re.match(r'^(\s*)', ln).group(1)
            lines[i] = f'{indent}const-string {reg}, "{POISON_URL}"  # poisoned: {url[:40]}...\n'
            dirty = True
            HITS += 1
            print(f"  {f.relative_to(APK)}:{i+1}  毒化 URL: {url[:60]}...")

        if dirty:
            f.write_text("".join(lines))
            MODS += 1

print(f"\n=== 补丁完成: {MODS} 个文件, {HITS} 个 URL 毒化为 {POISON_URL} ===")
