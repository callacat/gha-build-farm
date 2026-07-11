#!/usr/bin/env python3
"""红果短剧 去强制更新 v3 — v1基础 + UpgradePopupNewStyle"""
import sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
CHANGES = 0

def replace_all(path, olds, new):
    global CHANGES
    if not path.is_file(): return
    t = path.read_text("utf-8", errors="replace")
    hit = False
    for old in olds:
        if old in t:
            t = t.replace(old, new)
            hit = True
    if hit:
        path.write_text(t)
        CHANGES += 1
        print(f"  PATCH {path.relative_to(APK)}")

def find(pat):
    for sd in sorted(APK.glob("smali*")):
        if sd.is_dir():
            yield from sd.rglob(pat)

# ── 1. setCancelable(false) → true (skip AndroidX) ──
for f in find("*.smali"):
    r = str(f.relative_to(APK))
    if "/androidx/" in r or "/android/support/" in r: continue
    replace_all(f, ["setCancelable(false)"], "setCancelable(true)")
    replace_all(f, ["setCanceledOnTouchOutside(false)"], "setCanceledOnTouchOutside(true)")

# ── 2. PopDefiner force_upgrade → const null ──
for f in find("PopDefiner*.smali"):
    replace_all(f, ["sget-object v0, Lcom/dragon/read/pop/PopDefiner;->force_upgrade_dialog:Lcom/dragon/read/pop/PopDefiner$force_upgrade_dialog;",
                    "sget-object v1, Lcom/dragon/read/pop/PopDefiner;->force_upgrade_dialog:Lcom/dragon/read/pop/PopDefiner$force_upgrade_dialog;"],
               "const/4 v0, 0x0")

# ── 3. PushImpl → comment forceUpdate ──
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

# ── 4. ★ UpgradePopupNewStyle → dismiss instead of show ──
for f in find("UpgradePopupNewStyle.smali"):
    replace_all(f, ["->show()Z", "->show()V"], "->dismiss()V")

print(f"\n=== 补丁完成: {CHANGES} 处修改 ===")
