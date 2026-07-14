#!/usr/bin/env python3
"""Hongguo v7.2.7.32 — poison domains + disable checkUpdate"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
POISON = "127.0.0.1"
TARGETS = [
    "oneseeker.top", "171.43.214.186",
    "polaris5-normal-hl.zijieapi.com",
    "lf-normal-gr-sourcecdn.bytegecko.com",
    "idouyinvod.com", "dig.bdurl.net",
    "gecko5-hl.zijieapi.com", "mon11-misc-hl.fqnovel.com",
]

MODS = HITS = 0
RE_PATTERN = r'const-string\s+([vp\d]+)\s*,\s*"(https?://[^"]*'  # prefix before target
RE_SUFFIX = r'[^"]*)"'  # suffix after target

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
            for target in TARGETS:
                if target not in ln:
                    continue
                pattern = RE_PATTERN + re.escape(target) + RE_SUFFIX
                m = re.search(pattern, ln)
                if not m:
                    continue
                reg, url = m.group(1), m.group(2)
                indent = re.match(r"^(\s*)", ln).group(1)
                lines[i] = f'{indent}const-string {reg}, "http://{POISON}"  # blocked\n'
                dirty = True
                HITS += 1
                print(f"  {f.relative_to(APK)}:{i+1}  poison: {url[:50]}")
                break

        if "UpdateServiceImpl.smali" == f.name:
            for i, ln in enumerate(lines):
                if ".method public checkUpdate(" in ln:
                    close_paren = ln.find(")")
                    after_sig = ln[close_paren + 1:].lstrip() if close_paren >= 0 else ""
                    is_void = after_sig.startswith("V")
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if ".locals" in lines[j]:
                            indent = re.match(r"^(\s*)", lines[j]).group(1)
                            locals_m = re.search(r"\.locals\s+(\d+)", lines[j])
                            loc = int(locals_m.group(1)) if locals_m else 0
                            nls = [lines[j]]
                            if loc == 0 and not is_void:
                                nls[0] = f"{indent}.locals 1\n"
                            if is_void:
                                nls.append(f"{indent}return-void  # disabled\n")
                            else:
                                nls.append(f"{indent}const/4 v0, 0x0\n")
                                nls.append(f"{indent}return v0  # disabled (false)\n")
                            lines[j:j+1] = nls
                            dirty = True
                            HITS += 1
                            print(f"  {f.relative_to(APK)}:{i+1}  checkUpdate disabled (ret={'V' if is_void else 'Z'})")
                            break
                    break

        if dirty:
            f.write_text("".join(lines))
            MODS += 1

print(f"\n=== Done: {MODS} files, {HITS} hits ===")
