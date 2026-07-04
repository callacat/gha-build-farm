#!/usr/bin/env python3
"""红果短剧 去强制更新洗版 smali 补丁"""

import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
CHANGES = 0

def patch(path, kw, old, new):
    global CHANGES
    if not path.is_file(): return False
    t = path.read_text("utf-8", errors="replace")
    if old in t:
        path.write_text(t.replace(old, new))
        CHANGES += 1; print(f"  PATCH {path.relative_to(APK)}")
        return True
    if kw and kw not in t: return False
    return False

def comment_out_lines(path, markers):
    """Comment out lines by marker (multi-pass safe)."""
    global CHANGES
    if not path.is_file(): return
    t = path.read_text("utf-8", errors="replace")
    lines = t.splitlines(keepends=True)
    new = []
    hit = False
    for l in lines:
        s = l.strip()
        if any(m in s for m in markers) and not s.startswith("#"):
            new.append(f"# {l}")
            hit = True
        else:
            new.append(l)
    if hit:
        path.writelines(new)
        CHANGES += 1

def find_smali_files(pat):
    for sd in sorted(APK.glob("smali*")):
        if sd.is_dir():
            yield from sd.rglob(pat)

# ========== 1. Manifest ==========
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

# ========== 2. setCancelable(false) → true ==========
for f in find_smali_files("*.smali"):
    r = f.relative_to(APK)
    r_str = str(r)
    # Skip AndroidX / Android Support / Kotlin stdlib
    if r_str.startswith("smali/androidx/") or r_str.startswith("smali/android/support/"):
        continue
    if r_str.startswith("smali_classes") and ("androidx/" in r_str or "android/support/" in r_str):
        continue
    patch(f, "", "setCancelable(false)", "setCancelable(true)")
    patch(f, "", "setCanceledOnTouchOutside(false)", "setCanceledOnTouchOutside(true)")

# ========== 3. PopDefiner force_upgrade_dialog → NOP ==========
for f in find_smali_files("PopDefiner*.smali"):
    t = f.read_text("utf-8", errors="replace")
    o = t
    # Method that returns force_upgrade_dialog: replace with const/4 v0, 0x0
    t = re.sub(r'(sget-object\s+v\d+,) Lcom/dragon/read/pop/PopDefiner;->force_upgrade_dialog',
               r'const/4 \1 0x0\n    # force_upgrade_dialog disabled', t)
    # Any sget-object .*force_upgrade -> nop
    t = re.sub(r'sget-object\s+\w+,\s*Lcom/dragon/read/pop/PopDefiner;->force_upgrade_dialog[^;]*;',
               'const/4 v0, 0x0\n    # force_upgrade NOP', t)
    if t != o:
        f.write_text(t); CHANGES += 1
        print(f"  NOP force_upgrade in {f.relative_to(APK)}")

# ========== 4. forceUpdate field assignments → NOP ==========
for f in find_smali_files("*.smali"):
    r = str(f.relative_to(APK))
    if "PushImpl.smali" in r:
        comment_out_lines(f, ["forceUpdate"])

# ========== 5. NOP the whole com.ss.android.update package ==========
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    pkg_dir = sd / "com" / "ss" / "android" / "update"
    if pkg_dir.is_dir():
        for sm in pkg_dir.rglob("*.smali"):
            t = sm.read_text("utf-8", errors="replace")
            # Replace method bodies to just return void
            t = re.sub(r'\.method\s+.*onCreate.*',
                       '.method protected onCreate(Landroid/os/Bundle;)V\n    return-void\n.end method\n\n.method private original_onCreate', t)
            # Any invoke-virtual/invoke-direct in main method → NOP
            if t != sm.read_text("utf-8", errors="replace"):
                sm.write_text(t)
                CHANGES += 1
                print(f"  NOP {sm.relative_to(APK)}")

print(f"\n=== 补丁完成: {CHANGES} 处修改 ===")
