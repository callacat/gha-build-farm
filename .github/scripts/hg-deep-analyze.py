#!/usr/bin/env python3
"""红果短剧 深度分析：定位强制更新弹窗的精确调用链"""
import re, sys
from pathlib import Path
from collections import defaultdict

APKTOOL = Path("/tmp/apktool_out")
JADX = Path("/tmp/jadx_out")
FINDINGS = []

def log(tag, msg):
    FINDINGS.append(f"[{tag}] {msg}")
    print(f"  {tag}: {msg}")

def find_smali(pat):
    for sd in sorted(APKTOOL.glob("smali*")):
        if sd.is_dir():
            yield from sd.rglob(pat)

# === 1. Find ALL PopDefiner dialog types ===
log("POP", "=== All popup dialog types ===")
for f in find_smali("PopDefiner*.smali"):
    t = f.read_text("utf-8", errors="replace")
    for m in re.finditer(r'sget-object\s+(\w+),\s*Lcom/dragon/read/pop/PopDefiner;->(\w+):', t):
        log("POP", f"  {m.group(2)}")

# === 2. Find WHO calls force_upgrade_dialog ===
log("CALL", "=== Callers of force_upgrade ===")
for f in find_smali("*.smali"):
    r = str(f.relative_to(APKTOOL))
    if "androidx/" in r or "android/support/" in r: continue
    t = f.read_text("utf-8", errors="replace")
    if "force_upgrade" in t or "ForceUpgrade" in t or "forceUpgrade" in t:
        # Get method context
        methods = re.findall(r'\.method\s+.*\n(?:.*\n)*?(?=\.end method)', t, re.M)
        for m in methods:
            if 'force_upgrade' in m or 'ForceUpgrade' in m or 'forceUpgrade' in m:
                sig = m.split('\n')[0][:80]
                log("CALL", f"  {r}\n    {sig}")

# === 3. Find version check + dialog triggering ===
log("DIALOG", "=== Update dialog display ===")
for f in find_smali("*.smali"):
    r = str(f.relative_to(APKTOOL))
    if "androidx/" in r or "android/support/" in r: continue
    t = f.read_text("utf-8", errors="replace")
    # Look for update dialog builder patterns in app code
    if "AlertDialog" in t and ("version" in t.lower() or "update" in t.lower() or "升级" in t):
        log("DIALOG", f"  AlertDialog+update: {r}")

# === 4. Find webview update URL or app store check ===
log("URL", "=== Update URLs/endpoints ===")
for f in find_smali("*.smali"):
    t = f.read_text("utf-8", errors="replace")
    urls = re.findall(r'https?://[^"\'\s,)]+update[^"\'\s,)]*', t)
    for u in urls:
        log("URL", f"  {u[:100]}")

# === 5. Search jadx for update-related classes ===
log("JADX", "=== Update activities/dialogs in jadx ===")
for f in sorted(JADX.rglob("*.java")):
    r = str(f.relative_to(JADX))
    if "Update" in f.name or "Upgrade" in f.name:
        log("JADX", f"  {r}")

# === 6. Find the actual Pop triggering mechanism ===
log("POPCALL", "=== Pop dialog show() calls ===")
for f in find_smali("*.smali"):
    t = f.read_text("utf-8", errors="replace")
    r = str(f.relative_to(APKTOOL))
    if "androidx/" in r: continue
    # Find methods that call show() on a dialog
    if "->show()" in t and ("dialog" in t.lower() or "pop" in t.lower() or "upgrade" in t.lower()):
        log("POPCALL", f"  dialog show: {r}")

# === 7. Find checks that compare version codes ===
log("VER", "=== Version code comparisons ===")
for f in find_smali("*.smali"):
    t = f.read_text("utf-8", errors="replace")
    r = str(f.relative_to(APKTOOL))
    if "getVersionCode" in t or "getLongVersionCode" in t or "VERSION_CODE" in t:
        if "androidx/" not in r and "android/support/" not in r:
            log("VER", f"  {r}")

print(f"\n=== 分析完成: {len(FINDINGS)} 条发现 ===")
Path("/tmp/deep-analysis.txt").write_text("\n".join(FINDINGS))
