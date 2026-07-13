#!/usr/bin/env python3
"""Hongguo v7.2.7.32 -- disable force update dialogs

Strategy:
1. DialogFragment.forceUpdate hardcode to false
2. Global setCancelable(false) -> setCancelable(true)
3. Poison upgrade dialog enums (gray_upgrade, official_upgrade, force_upgrade)
4. LuckyDogLowUpdateDialog.O1() finish + return-void
"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0
HITS = 0

# Strategy 1: DialogFragment forceUpdate
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
    print("S1: found " + str(target.relative_to(APK)))
    t = target.read_text("utf-8", errors="replace")
    lines = t.splitlines(keepends=True)
    d = False
    for i, ln in enumerate(lines):
        m = re.search(r'iput-boolean\s+(v\d+|p\d+),\s*p0,\s*L[^;]+;->forceUpdate:Z', ln)
        if m:
            reg = m.group(1)
            indent = re.match(r'^(\s*)', ln).group(1)
            lines[i] = indent + 'const/4 ' + reg + ', 0x0  # force false\n' + ln
            d = True; HITS += 1
    if d:
        target.write_text("".join(lines)); MODS += 1
else:
    print("S1: not found")

# Strategy 2: setCancelable
print("\nS2: setCancelable(false)->true")
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        if "/androidx/" in r or "/annotation/" in r: continue
        t = f.read_text("utf-8", errors="replace")
        lines = t.splitlines(keepends=True)
        d = False
        for i, ln in enumerate(lines):
            if 'setCancelable' not in ln: continue
            for j in range(max(0, i-5), i):
                prev = lines[j]
                m = re.search(r'const/4\s+(v\d+),\s*0x0', prev)
                if m and m.group(1) in ln:
                    indent = re.match(r'^(\s*)', prev).group(1)
                    lines[j] = indent + 'const/4 ' + m.group(1) + ', 0x1  # patch\n'
                    d = True; HITS += 1
                    break
        if d:
            f.write_text("".join(lines)); MODS += 1

# Strategy 3: poison pop enums
print("\nS3: poison upgrade enums")
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        t = f.read_text("utf-8", errors="replace")
        lines = t.splitlines(keepends=True)
        d = False
        if "gray_upgrade_dialog" in r or "official_upgrade_dialog" in r or "force_upgrade_dialog" in r:
            for i, ln in enumerate(lines):
                if "isFunctionality" in ln and "Z" in ln:
                    for j in range(i+1, min(i+3, len(lines))):
                        if "const/4" in lines[j]:
                            indent = re.match(r'^(\s*)', lines[j]).group(1)
                            lines[j] = indent + 'const/4 v0, 0x0  # disable\n'
                            d = True; HITS += 1
                            break
                    break
        if d:
            f.write_text("".join(lines)); MODS += 1

# Strategy 4: LuckyDogLowUpdateDialog.P1() shortcut (actual onCreate body)
# P1(Intent, Bundle) is the real init after Lancet proxy T1
print("\nS4: shortcut LuckyDogLowUpdateDialog.P1()")
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        if f.name != "LuckyDogLowUpdateDialog.smali": continue
        t = f.read_text("utf-8", errors="replace")
        lines = t.splitlines(keepends=True)
        d = False
        for i, ln in enumerate(lines):
            if '.method public P1(Landroid/content/Intent;Landroid/os/Bundle;)V' in ln:
                # Find .locals and insert return-void right after
                for j in range(i+1, min(i+5, len(lines))):
                    if '.locals' in lines[j]:
                        indent = re.match(r'^(\s*)', lines[j]).group(1)
                        lines.insert(j+1, indent + 'return-void  # ponytail: skip LuckyDogLowUpdateDialog\n')
                        d = True; HITS += 1
                        print("  " + str(f.relative_to(APK)) + ":" + str(j+1) + "  P1() -> return-void")
                        break
                break
        if d:
            f.write_text("".join(lines)); MODS += 1

print("\n=== Done: " + str(MODS) + " files, " + str(HITS) + " hits ===")
