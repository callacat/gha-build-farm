#!/usr/bin/env python3
"""红果短剧 去强制更新 — 只改 smali，资源不动"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
CHANGES = 0

def replace_in(path, olds, new):
    global CHANGES
    if not path.is_file(): return
    t = path.read_text("utf-8", errors="replace")
    for old in olds:
        if old in t and t.count(old) > 0:
            t = t.replace(old, new)
            CHANGES += 1
    path.write_text(t)

def find(pat):
    for sd in sorted(APK.glob("smali*")):
        if sd.is_dir():
            yield from sd.rglob(pat)

# ===== 1. ALL setCancelable(false) → true (skip AndroidX) =====
for f in find("*.smali"):
    r = str(f.relative_to(APK))
    if "androidx/" in r or "android/support/" in r: continue
    replace_in(f, ["setCancelable (false)", "setCancelable(false)"], "setCancelable(true)")
    replace_in(f, ["setCanceledOnTouchOutside (false)", "setCanceledOnTouchOutside(false)"], "setCanceledOnTouchOutside(true)")

# ===== 2. PopDefiner force_upgrade → const null =====
for f in find("PopDefiner*.smali"):
    replace_in(f, [
        "sget-object v0, Lcom/dragon/read/pop/PopDefiner;->force_upgrade_dialog:Lcom/dragon/read/pop/PopDefiner$force_upgrade_dialog;",
        "sget-object v1, Lcom/dragon/read/pop/PopDefiner;->force_upgrade_dialog:Lcom/dragon/read/pop/PopDefiner$force_upgrade_dialog;",
    ], "const/4 v0, 0x0")

# ===== 3. Disable update methods by patching return values =====
for f in find("*.smali"):
    r = str(f.relative_to(APK))
    # Force-return false in check methods
    if "checkUpdate" in r or "ForceUpdate" in r:
        replace_in(f, ["const/4 v0, 0x1", "const/4 v1, 0x1"], "const/4 v0, 0x0")

# ===== 4. Disable UpdateProgressActivity by patching onCreate =====
for f in find("UpdateProgressActivity.smali"):
    replace_in(f, [
        "invoke-super",  # first thing in onCreate becomes return
        "invoke-direct",
    ], "# patched")

# ===== 5. PushImpl forceUpdate =====
for f in find("PushImpl.smali"):
    replace_in(f, ["forceUpdate"], "forceUpdatePATCHED")

# ===== 6. LuckyDog low update dialog =====
for f in find("LuckyDogLowUpdateDialog.smali"):
    replace_in(f, ["invoke-super", "invoke-direct"], "# disabled")

print(f"\n=== 补丁完成: {CHANGES} 处修改 ===")
