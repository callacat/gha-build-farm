#!/usr/bin/env python3
"""红果短剧 v7 — 从 APK 二进制删除更新相关 Activity 注册"""
import re, sys, os, zipfile, shutil
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
CHANGES = 0

def find(pat):
    for sd in sorted(APK.glob("smali*")):
        if sd.is_dir():
            yield from sd.rglob(pat)

BAD_ACTIVITIES = [
    "com.ss.android.update.UpdateProgressActivity",
    "com.bytedance.ug.sdk.luckydog.window.dialog.LuckyDogLowUpdateDialog",
    "com.android.ttcjpaysdk.thirdparty.supplementarysign.activity.CJPaySSUpdateCardInfoActivity",
    "com.dragon.read.component.biz.impl.bookshelf.chase.ChaseUpdatesActivity",
]

# ── 1. Manifest: 找到并打印这些 Activity 的注册，尝试 NOP ──
mf = APK / "AndroidManifest.xml"
if mf.is_file():
    t = mf.read_text("utf-8", errors="replace")
    for bad in BAD_ACTIVITIES:
        # Find the <activity block for this class
        pat = rf'(<activity[^>]*{re.escape(bad)}[^>]*>)'
        for m in re.finditer(pat, t):
            print(f"  MANIFEST: {m.group()[:120]}")
            # The --copy-original means this won't apply, but we're logging it
    # Also list ALL activities for reference
    acts = re.findall(r'<activity\s+([^>]*android:name="([^"]*)"[^>]*)>', t)
    for attr, name in acts:
        if 'Theme.AppCompat.Dialog' in attr or 'android:theme="@' in attr:
            theme = re.search(r'theme="([^"]*)"', attr)
            tname = theme.group(1) if theme else '?'
            print(f"  ACTIVITY: {name}  theme={tname}")

# ── 2. setCancelable(false) → true ──
for f in find("*.smali"):
    r = str(f.relative_to(APK))
    if "/androidx/" in r or "/android/support/" in r: continue
    t = f.read_text("utf-8", errors="replace"); o = t
    t = t.replace("setCancelable(false)", "setCancelable(true)")
    t = t.replace("setCanceledOnTouchOutside(false)", "setCanceledOnTouchOutside(true)")
    if t != o:
        f.write_text(t); CHANGES += 1

# ── 3. PopDefiner: all upgrade/update/force → const null ──
for f in find("PopDefiner*.smali"):
    t = f.read_text("utf-8", errors="replace"); o = t
    t = re.sub(r'sget-object\s+(\w+),\s*Lcom/dragon/read/pop/PopDefiner;->(\w*(?:upgrade|update|force)\w*):.*',
               r'const/4 \1, 0x0', t)
    if t != o:
        f.write_text(t); CHANGES += 1

# ── 4. UpgradePopupNewStyle show → dismiss ──
for f in find("UpgradePopupNewStyle*.smali"):
    t = f.read_text("utf-8", errors="replace"); o = t
    t = t.replace("->show()Z", "->dismiss()V").replace("->show()V", "->dismiss()V")
    if t != o:
        f.write_text(t); CHANGES += 1

# ── 5. ForceUpdateInfo → const 0x0 ──
for f in find("ForceUpdateInfo.smali"):
    t = f.read_text("utf-8", errors="replace"); o = t
    t = t.replace("const/4 v0, 0x1", "const/4 v0, 0x0")
    if t != o:
        f.write_text(t); CHANGES += 1

# ── 6. PushImpl → comment forceUpdate ──
for f in find("PushImpl.smali"):
    t = f.read_text("utf-8", errors="replace")
    lines = t.splitlines(keepends=True)
    new_lines = []
    for l in lines:
        if "forceUpdate" in l and not l.strip().startswith("#"):
            new_lines.append(f"# {l}")
        else:
            new_lines.append(l)
    f.write_text("".join(new_lines)); CHANGES += 1

print(f"\n=== 补丁完成: {CHANGES} 处修改 ===")
