#!/usr/bin/env python3
"""红果短剧 去强制更新 v2 — 针对真实调用链"""
import sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
CHANGES = 0

def find(pat):
    for sd in sorted(APK.glob("smali*")):
        if sd.is_dir():
            yield from sd.rglob(pat)

for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        if "/androidx/" in r or "/android/support/" in r: continue
        t = f.read_text("utf-8", errors="replace")
        o = t

        # ── 1. NsUpdateServiceImpl → return early ──
        if "NsUpdateServiceImpl" in r:
            # Replace the check/update method body: make it return-void
            if "onGetAppUpdateConfig" in t or "checkForceUpdate" in t or "doUpdate" in t:
                t = t.replace("invoke-super", "return-void\n    # NsUpdateServiceImpl disabled")
                t = t.replace("invoke-direct", "return-void\n    # NsUpdateServiceImpl disabled")

        # ── 2. UpgradePopupNewStyle → NOP ──
        if "UpgradePopupNewStyle" in r:
            if ".method" in t and "onCreate" in t:
                t = t.replace(".method protected onCreate", ".method protected onCreate\n    return-void\n    # UpgradePopupNewStyle disabled\n\n    .method private original_onCreate")
            if "show()" in t:
                t = t.replace("->show()", "->dismiss()")

        # ── 3. ForceUpdateInfoResponse → forceUpdate field = false ──
        if "ForceUpdateInfo" in r:
            # Replace any const/4 vX, 0x1 that sets force update
            t = t.replace("const/4 v0, 0x1", "const/4 v0, 0x0")
            t = t.replace("const/4 v1, 0x1", "const/4 v1, 0x0")
            # Force field getter to return false
            if "forceUpdate" in t:
                t = t.replace("->forceUpdate", "->forceUpdate_disabled")

        # ── 4. UpdateService → finish immediately ──
        if "UpdateService" in r:
            if "onStartCommand" in t or "onHandleIntent" in t or "onStart" in t:
                t = t.replace("invoke-super", "return-void\n    # UpdateService disabled")

        # ── 5. setCancelable (already working) ──
        if "setCancelable(false)" in t:
            t = t.replace("setCancelable(false)", "setCancelable(true)")
        if "setCanceledOnTouchOutside(false)" in t:
            t = t.replace("setCanceledOnTouchOutside(false)", "setCanceledOnTouchOutside(true)")

        # ── 6. AppUpdateConfig → disable ──
        if "AppUpdateConfig" in r and "config" in t.lower():
            t = t.replace("const/4 v0, 0x1", "const/4 v0, 0x0")

        if t != o:
            f.write_text(t)
            CHANGES += 1

print(f"\n=== 补丁完成: {CHANGES} 处修改 ===")
