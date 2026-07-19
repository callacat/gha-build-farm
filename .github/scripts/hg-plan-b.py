#!/usr/bin/env python3
import sys
"""方案B: 删除包含 oneseeker/remote.oneseeker/dongle.oneseeker 的 const-string 行"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TARGETS = ["oneseeker.top", "remote.oneseeker.top", "dongle.oneseeker.top"]
MODS = HITS = 0

for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        if "/androidx/" in r: continue
        text = f.read_text("utf-8", errors="replace")
        target = next((t for t in TARGETS if t in text), None)
        if not target: continue
        lines = text.splitlines(keepends=True)
        dirty = False
        new_lines = []
        for i, ln in enumerate(lines):
            if target in ln and ("const-string" in ln or "const-string/jumbo" in ln):
                indent = re.match(r"^(\s*)", ln).group(1)
                reg_match = re.search(r'(const-string\s+(?:/jumbo\s+)?[vp]\d+)', ln)
                if reg_match:
                    new_lines.append(f"{indent}{reg_match.group(1)}, \"\"  # empty: {target} blocked\n")
                else:
                    new_lines.append(f"{indent}# {target} blocked\n")
                HITS += 1
                print(f"  [B] {r}:{i+1} emptied")
                dirty = True
            else:
                new_lines.append(ln)
        if dirty:
            f.write_text("".join(new_lines), encoding="utf-8")
            MODS += 1
print(f"=== 方案B Done: {MODS} files, {HITS} hits ===")
