#!/usr/bin/env python3
"""红果短剧 去强制更新 smali 补丁 — 暴力版"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
CHANGES = 0

def replace_all(path, olds, new):
    global CHANGES
    if not path.is_file(): return
    t = path.read_text("utf-8", errors="replace")
    for old in olds:
        if old in t:
            t = t.replace(old, new)
            CHANGES += 1
            print(f"  PATCH {path.relative_to(APK)}: {old[:60]}")
    path.write_text(t)

def find(pat):
    for sd in sorted(APK.glob("smali*")):
        if sd.is_dir():
            yield from sd.rglob(pat)

# ===== 1. Manifest: disable update activities =====
mf = APK / "AndroidManifest.xml"
if mf.is_file():
    t = mf.read_text("utf-8"); o = t
    for act in [
        "com.ss.android.update.UpdateProgressActivity",
        "com.bytedance.ug.sdk.luckydog.window.dialog.LuckyDogLowUpdateDialog",
    ]:
        t = re.sub(rf'(<activity[^>]*name="{act}"[^>]*)(/?>)',
                   r'\1 android:enabled="false"\2', t)
    if t != o:
        mf.write_text(t); CHANGES += 1
        print("  PATCH AndroidManifest.xml")

# ===== 2. setCancelable(false) → true (skip only AndroidX) =====
for f in find("*.smali"):
    r = str(f.relative_to(APK))
    if "androidx/" in r or "android/support/" in r: continue
    replace_all(f, ["setCancelable(false)", "setCancelable (false)"], "setCancelable(true)")
    replace_all(f, ["setCanceledOnTouchOutside(false)", "setCanceledOnTouchOutside (false)"], "setCanceledOnTouchOutside(true)")

# ===== 3. PopDefiner: ANY force_upgrade reference → const/4 =====
for f in find("*.smali"):
    r = str(f.relative_to(APK))
    if "PopDefiner" not in r: continue
    replace_all(f, [
        "force_upgrade_dialog",
        "force_upgrade",
    ], "force_upgrade_NOP")

# ===== 4. UpdateProgressActivity → stop it from showing =====
for f in find("UpdateProgressActivity.smali"):
    replace_all(f, [
        "->onCreate",
        "onCreate",
    ], "onCreate_BLOCKED")

# ===== 5. Disable update check methods via const/4 v0, 0x0 =====
for f in find("*.smali"):
    r = str(f.relative_to(APK))
    # NOP version compare methods
    if "checkUpdate" in r or "ForceUpdate" in r or "forceUpdate" in r:
        replace_all(f, [
            "const/4 v0, 0x1",
            "const/4 v1, 0x1",
        ], "const/4 v0, 0x0")

# ===== 6. PushImpl =====
for f in find("PushImpl.smali"):
    replace_all(f, ["forceUpdate"], "forceUpdate_disabled")

print(f"\n=== 补丁完成: {CHANGES} 处修改 ===")
