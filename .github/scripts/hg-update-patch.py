#!/usr/bin/env python3
"""Only: setCancelable(false)->true + forceUpdate->false + upgrade enums.
No P1 shortcut. Stable version that user confirmed works (except white dialog)."""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = HITS = 0

# S1: forceUpdate
target = None
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        try:
            t = f.read_text("utf-8", errors="replace")
            if re.search(r'\.super.*DialogFragment', t) and re.search(r'\.field.*forceUpdate:Z', t):
                target = f; break
        except: continue
    if target: break
if target:
    t = target.read_text("utf-8", errors="replace")
    lines = t.splitlines(keepends=True); d = False
    for i, ln in enumerate(lines):
        m = re.search(r'iput-boolean\s+(v\d+|p\d+),\s*p0,\s*L[^;]+;->forceUpdate:Z', ln)
        if m:
            reg, indent = m.group(1), re.match(r'^(\s*)', ln).group(1)
            lines[i] = indent + 'const/4 ' + reg + ', 0x0\n' + ln; d = True; HITS += 1
    if d: target.write_text("".join(lines)); MODS += 1
    print(f"S1: {HITS} hit(s)")
else: print("S1: not found")

# S2: setCancelable
print("S2: setCancelable")
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        if "/androidx/" in r or "/annotation/" in r: continue
        t = f.read_text("utf-8", errors="replace")
        lines = t.splitlines(keepends=True); d = False
        for i, ln in enumerate(lines):
            if 'setCancelable' not in ln: continue
            for j in range(max(0, i-5), i):
                prev = lines[j]
                m = re.search(r'const/4\s+(v\d+),\s*0x0', prev)
                if m and m.group(1) in ln:
                    indent = re.match(r'^(\s*)', prev).group(1)
                    lines[j] = indent + 'const/4 ' + m.group(1) + ', 0x1\n'
                    d = True; HITS += 1; break
        if d: f.write_text("".join(lines)); MODS += 1
        if HITS % 20 == 0 and HITS > 0: print(f"  ... {HITS}")

# S3: upgrade enums
print("S3: upgrade enums")
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        if not ("gray_upgrade_dialog" in r or "official_upgrade_dialog" in r or "force_upgrade_dialog" in r): continue
        t = f.read_text("utf-8", errors="replace")
        lines = t.splitlines(keepends=True); d = False
        for i, ln in enumerate(lines):
            if "isFunctionality" in ln and "Z" in ln:
                for j in range(i+1, min(i+3, len(lines))):
                    if "const/4" in lines[j]:
                        indent = re.match(r'^(\s*)', lines[j]).group(1)
                        lines[j] = indent + 'const/4 v0, 0x0\n'
                        d = True; HITS += 1; break
                break
        if d: f.write_text("".join(lines)); MODS += 1

# S4: capture ONLY — dump top activity/focus 10s after launch
# This is just informational, no additional patching

print(f"\n=== Done: {MODS} files, {HITS} hits ===")
