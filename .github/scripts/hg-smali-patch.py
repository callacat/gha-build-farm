#!/usr/bin/env python3
"""红果短剧 去强制更新 smali 补丁 — 不碰方法体，只做安全替换"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
CHANGES = 0

def replace_in(path, old, new):
    global CHANGES
    if not path.is_file(): return
    t = path.read_text("utf-8", errors="replace")
    if old not in t: return
    path.write_text(t.replace(old, new))
    CHANGES += 1; print(f"  PATCH {path.relative_to(APK)}")

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
        "com.android.ttcjpaysdk.thirdparty.supplementarysign.activity.CJPaySSUpdateCardInfoActivity",
    ]:
        t = re.sub(rf'(<activity[^>]*name="{act}"[^>]*)(/?>)',
                   r'\1 android:enabled="false"\2', t)
    if t != o:
        mf.write_text(t); CHANGES += 1
        print("  PATCH AndroidManifest.xml: disabled update activities")

# ===== 2. setCancelable(false) → true =====
for f in find("*.smali"):
    r = str(f.relative_to(APK))
    if r.startswith(("smali/androidx/", "smali/android/support/")): continue
    if "/androidx/" in r or "/android/support/" in r: continue
    replace_in(f, "setCancelable(false)", "setCancelable(true)")
    replace_in(f, "setCanceledOnTouchOutside(false)", "setCanceledOnTouchOutside(true)")

# ===== 3. PopDefiner: force_upgrade_dialog → const null =====
for f in find("PopDefiner*.smali"):
    replace_in(f,
        "sget-object v0, Lcom/dragon/read/pop/PopDefiner;->force_upgrade_dialog:Lcom/dragon/read/pop/PopDefiner$force_upgrade_dialog;",
        "const/4 v0, 0x0")

# ===== 4. PushImpl: forceUpdate references → comment =====
for f in find("PushImpl.smali"):
    t = f.read_text("utf-8", errors="replace")
    lines = t.splitlines(keepends=True)
    new = []
    for l in lines:
        if "forceUpdate" in l and not l.strip().startswith("#"):
            new.append(f"# {l}")
        else:
            new.append(l)
    f.write_text("".join(new)); CHANGES += 1
    print(f"  COMMENT forceUpdate in {f.relative_to(APK)}")

print(f"\n=== 补丁完成: {CHANGES} 处修改 ===")
