#!/usr/bin/env python3
"""红果短剧 去强制更新 v8 — 字节码级弹窗拦截"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0
HITS = {"cancelable": 0, "tOutside": 0}


def find(pat):
    for sd in sorted(APK.glob("smali*")):
        if sd.is_dir():
            yield from sd.rglob(pat)


def find_const_0x0(lines: list[str], reg: str, up_to: int) -> int | None:
    """在 up_to 前查 const/4|16 vREG, 0x0"""
    for j in range(up_to - 1, max(up_to - 10, 0), -1):
        if re.match(r'^\s*const(?:/4|/16)?\s+' + re.escape(reg) + r',\s*0x0\s*$', lines[j]):
            return j
        if re.match(r'^\s*const', lines[j]) and re.search(re.escape(reg), lines[j]):
            return None
    return None


for f in find("*.smali"):
    r = str(f.relative_to(APK))
    if "/androidx/" in r or "/annotation/" in r:
        continue
    t = f.read_text("utf-8", errors="replace")
    lines = t.splitlines(keepends=True)
    dirty = False

    for target in ("setCancelable", "setCanceledOnTouchOutside"):
        for i, ln in enumerate(lines):
            m = re.search(
                r'invoke-virtual\s*\{([vp\d]+)\},.*;->' + target + r'\(Z\)',
                ln,
            )
            if not m:
                continue
            ci = find_const_0x0(lines, m.group(1), i)
            if ci is None:
                continue
            lines[ci] = lines[ci].replace("0x0", "0x1")
            dirty = True
            HITS[target if target == "setCancelable" else "tOutside"] += 1
            print(f"  {f.relative_to(APK)}:{i+1}  {target} false→true")

    if dirty:
        f.write_text("".join(lines))
        MODS += 1

print(f"\n=== 补丁完成: {MODS} 个文件，{HITS['cancelable']}×setCancelable, {HITS['tOutside']}×canceledOnTouchOutside ===")
