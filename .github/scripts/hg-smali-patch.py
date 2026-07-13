#!/usr/bin/env python3
"""Hongguo v7.2.7.32 - poison domains + disable checkUpdate (exact filename match)"""
import re, sys
from pathlib import Path
APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
POISON = "127.0.0.1"
TARGETS = ["oneseeker.top","171.43.214.186","polaris5-normal-hl.zijieapi.com","lf-normal-gr-sourcecdn.bytegecko.com","idouyinvod.com","dig.bdurl.net","gecko5-hl.zijieapi.com","mon11-misc-hl.fqnovel.com"]
MODS = HITS = 0
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        if "/androidx/" in r or "/annotation/" in r: continue
        t = f.read_text("utf-8", errors="replace"); lines = t.splitlines(keepends=True); dirty = False
        for i, ln in enumerate(lines):
            for target in TARGETS:
                if target not in ln: continue
                m = re.search(r"const-string\s+([vp\d]+)\s*,\s*"(https?://[^"]*" + re.escape(target) + r[^]*), ln)
                if not m: continue
                reg, url = m.group(1), m.group(2)
                indent = re.match(r"^(\s*)", ln).group(1)
                lines[i] = f"{indent}const-string {reg}, "http://{POISON}"  # blocked
"
                dirty = True; HITS += 1; print(f"  {f.relative_to(APK)}:{i+1}  poison: {url[:50]}")
                break
        if "UpdateServiceImpl.smali" == f.name:
            for i, ln in enumerate(lines):
                if ".method public checkUpdate(" in ln:
                    for j in range(i+1, min(i+5, len(lines))):
                        if ".locals" in lines[j]:
                            indent = re.match(r"^(\s*)", lines[j]).group(1)
                            lines.insert(j+1, f"{indent}return-void  # disabled
")
                            dirty = True; HITS += 1; print(f"  {f.relative_to(APK)}:{i+1}  checkUpdate disabled")
                            break
                    break
        if dirty: f.write_text("".join(lines)); MODS += 1
print(f"
=== Done: {MODS} files, {HITS} hits ===")
