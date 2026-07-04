#!/usr/bin/env python3
"""红果短剧 去强制更新 smali 补丁"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
CHANGES = 0

def patch_file(path, old, new):
    global CHANGES
    if not path.is_file(): return
    t = path.read_text("utf-8", errors="replace")
    if old in t:
        path.write_text(t.replace(old, new))
        CHANGES += 1; print(f"  PATCH {path.relative_to(APK)}")

def comment_lines(path, markers):
    global CHANGES
    if not path.is_file(): return
    t = path.read_text("utf-8", errors="replace")
    lines = t.splitlines(keepends=True)
    new, hit = [], False
    for l in lines:
        s = l.strip()
        if any(m in s for m in markers) and not s.startswith("#"):
            new.append(f"# {l}"); hit = True
        else:
            new.append(l)
    if hit:
        path.write_text("".join(new)); CHANGES += 1

def find_files(pat):
    for sd in sorted(APK.glob("smali*")):
        if sd.is_dir():
            yield from sd.rglob(pat)

# ===== 1. Manifest: disable update activities =====
mf = APK / "AndroidManifest.xml"
if mf.is_file():
    t = mf.read_text("utf-8")
    o = t
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

# ===== 2. setCancelable(false) → true (skip AndroidX) =====
for f in find_files("*.smali"):
    r = str(f.relative_to(APK))
    if r.startswith(("smali/androidx/", "smali/android/support/")):
        continue
    if any(x in r for x in ("/androidx/", "/android/support/")):
        continue
    patch_file(f, "setCancelable(false)", "setCancelable(true)")
    patch_file(f, "setCanceledOnTouchOutside(false)", "setCanceledOnTouchOutside(true)")

# ===== 3. PopDefiner: NOP force_upgrade_dialog =====
for f in find_files("PopDefiner*.smali"):
    t = f.read_text("utf-8", errors="replace")
    o = t
    t = re.sub(r'sget-object\s+\w+,\s*Lcom/dragon/read/pop/PopDefiner;->force_upgrade_dialog[^;]*;',
               'const/4 v0, 0x0\n    # force_upgrade_dialog NOP', t)
    if t != o:
        f.write_text(t); CHANGES += 1
        print(f"  NOP force_upgrade {f.relative_to(APK)}")

# ===== 4. PushImpl: comment out forceUpdate refs =====
for f in find_files("PushImpl.smali"):
    comment_lines(f, ["forceUpdate"])
    print(f"  COMMENT forceUpdate in {f.relative_to(APK)}")

# ===== 5. NOP com.ss.android.update package =====
for sd in sorted(APK.glob("smali*")):
    pkg = sd / "com" / "ss" / "android" / "update"
    if pkg.is_dir():
        for sm in pkg.rglob("*.smali"):
            t = sm.read_text("utf-8", errors="replace")
            o = t
            # Replace first non-empty method with return-void
            t = re.sub(r'(\.method\s+(?:public|private|protected).*onCreate.*)',
                       '.method protected onCreate(Landroid/os/Bundle;)V\n    return-void\n.end method\n\n# PATCHED: original_onCreate', t, count=1)
            if t != o:
                sm.write_text(t); CHANGES += 1
                print(f"  NOP {sm.relative_to(APK)}")

# ===== 6. LuckyDogLowUpdateDialog: replace finish() with return-void =====
for f in find_files("LuckyDogLowUpdateDialog.smali"):
    t = f.read_text("utf-8", errors="replace")
    o = t
    t = re.sub(r'(\.method\s+(?:public|private|protected).*onCreate.*)',
               '.method protected onCreate(Landroid/os/Bundle;)V\n    return-void\n.end method\n\n# PATCHED: dialog disabled', t, count=1)
    if t != o:
        f.write_text(t); CHANGES += 1
        print(f"  NOP {f.relative_to(APK)}")

print(f"\n=== 补丁完成: {CHANGES} 处修改 ===")
