#!/usr/bin/env python3
"""红果短剧 v7.2.7.32 -- 禁用强制更新弹窗

策略（按优先级）：
1. DialogFragment.forceUpdate 硬编码为 false
2. 全局 setCancelable(false) -> setCancelable(true)
3. 毒化升级弹窗枚举（gray_upgrade + official_upgrade + force_upgrade）
4. LuckyDogLowUpdateDialog.O1() finish + return-void
"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0
HITS = 0

# ========== 策略 1 ==========
target_class = None
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        try:
            t = f.read_text("utf-8", errors="replace")
            if re.search(r'\.super.*DialogFragment', t) and re.search(r'\.field.*forceUpdate:Z', t):
                target_class = f
                break
        except:
            continue
    if target_class: break

if target_class:
    print(f"策略1: 找到目标类 {target_class.relative_to(APK)}")
    t = target_class.read_text("utf-8", errors="replace")
    lines = t.splitlines(keepends=True)
    dirty = False
    for i, ln in enumerate(lines):
        m = re.search(r'iput-boolean\s+(v\d+|p\d+),\s*p0,\s*L[^;]+;->forceUpdate:Z', ln)
        if m:
            reg = m.group(1)
            indent = re.match(r'^(\s*)', ln).group(1)
            lines[i] = f'{indent}const/4 {reg}, 0x0  # force forceUpdate=false\n{ln}'
            dirty = True; HITS += 1
            print(f"  {target_class.relative_to(APK)}:{i+1}  forceUpdate -> false")
    if dirty:
        target_class.write_text("".join(lines)); MODS += 1
else:
    print("策略1: 未找到 DialogFragment+forceUpdate")

# ========== 策略 2 ==========
print("\n策略2: setCancelable(false) -> true")
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        if "/androidx/" in r or "/annotation/" in r: continue
        t = f.read_text("utf-8", errors="replace")
        lines = t.splitlines(keepends=True)
        dirty = False
        for i, ln in enumerate(lines):
            if 'setCancelable' not in ln: continue
            for j in range(max(0, i-5), i):
                prev = lines[j]
                m = re.search(r'const/4\s+(v\d+),\s*0x0', prev)
                if m and m.group(1) in ln:
                    reg, indent = m.group(1), re.match(r'^(\s*)', prev).group(1)
                    lines[j] = f'{indent}const/4 {reg}, 0x1  # patch: true\n'
                    dirty = True; HITS += 1
                    print(f"  {f.relative_to(APK)}:{j+1}  setCancelable false->true")
                    break
        if dirty:
            f.write_text("".join(lines)); MODS += 1

# ========== 策略 3 ==========
print("\n策略3: 毒化升级弹窗枚举")
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        t = f.read_text("utf-8", errors="replace")
        lines = t.splitlines(keepends=True)
        dirty = False
        if "gray_upgrade_dialog" in r or "official_upgrade_dialog" in r or "force_upgrade_dialog" in r:
            for i, ln in enumerate(lines):
                if "isFunctionality" in ln and "Z" in ln:
                    for j in range(i+1, min(i+3, len(lines))):
                        if "const/4" in lines[j] and ("0x1" in lines[j] or "0x0" in lines[j]):
                            indent = re.match(r'^(\s*)', lines[j]).group(1)
                            lines[j] = f'{indent}const/4 v0, 0x0  # ponytail: disable\n'
                            dirty = True; HITS += 1
                            print(f"  {f.relative_to(APK)}:{j+1}  isFunctionality -> false")
                            break
                    break
        if dirty:
            f.write_text("".join(lines)); MODS += 1

# ========== 策略 4: LuckyDogLowUpdateDialog ==========
print("\n策略4: 短路 LuckyDogLowUpdateDialog")
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        if f.name != "LuckyDogLowUpdateDialog.smali": continue
        t = f.read_text("utf-8", errors="replace")
        lines = t.splitlines(keepends=True)
        dirty = False
        for i, ln in enumerate(lines):
            m = re.search(r'\.method\s+(public\s+)?static\s+(final\s+)?(protected\s+)?(void\s+)?O1\(', ln)
            if m:
                indent = re.match(r'^(\s*)', ln).group(1)
                lines.insert(i+1, f'{indent}invoke-virtual {{p0}}, Lcom/bytedance/ug/sdk/luckydog/window/dialog/LuckyDogLowUpdateDialog;->finish()V\n')
                lines.insert(i+2, f'{indent}return-void  # ponytail: skip\n')
                dirty = True; HITS += 1
                print(f"  {f.relative_to(APK)}:{i+1}  O1() finish + return-void")
                break
        if dirty:
            f.write_text("".join(lines)); MODS += 1
            print(f"  -> {f.relative_to(APK)} patched")

if not HITS:
    print("\n  === 无修改 ===")
print(f"\n=== 补丁完成: {MODS} 文件, {HITS} 处 ===")
