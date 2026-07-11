#!/usr/bin/env python3
"""红果短剧 去强制更新 v4 — 全面拦截所有升级弹窗，仅安全替换"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
CHANGES = 0

def replace_in(path, old, new):
    global CHANGES
    if not path.is_file(): return
    t = path.read_text("utf-8", errors="replace")
    if old not in t: return
    t = t.replace(old, new)
    path.write_text(t)
    CHANGES += 1
    print(f"  PATCH {path.relative_to(APK)}")

def find(pat):
    for sd in sorted(APK.glob("smali*")):
        if sd.is_dir():
            yield from sd.rglob(pat)

# ── 1. PopDefiner: NOP ALL upgrade/update/force dialog references ──
for f in find("PopDefiner*.smali"):
    t = f.read_text("utf-8", errors="replace"); o = t
    t = re.sub(r'sget-object\s+(\w+),\s*Lcom/dragon/read/pop/PopDefiner;->(\w*(?:upgrade|update|force)\w*):.*',
               r'const/4 \1, 0x0  # \2 NOP', t)
    if t != o:
        f.write_text(t); CHANGES += 1
        print(f"  NOP upgrade/force dialogs in {f.relative_to(APK)}")

# ── 2. UpgradePopupNewStyle show → dismiss ──
for f in find("UpgradePopupNewStyle*.smali"):
    replace_in(f, "->show()Z", "->dismiss()V")
    replace_in(f, "->show()V", "->dismiss()V")

# ── 3. LuckyDogLowUpdateDialog show → dismiss ──
for f in find("LuckyDogLowUpdateDialog.smali"):
    replace_in(f, "->show()Z", "->dismiss()V")
    replace_in(f, "->show()V", "->dismiss()V")

# ── 4. ForceUpdateInfo → return false ──
for f in find("ForceUpdateInfo.smali"):
    replace_in(f, "const/4 v0, 0x1", "const/4 v0, 0x0")

# ── 5. setCancelable (skip AndroidX) ──
for f in find("*.smali"):
    r = str(f.relative_to(APK))
    if "/androidx/" in r or "/android/support/" in r: continue
    replace_in(f, "setCancelable(false)", "setCancelable(true)")
    replace_in(f, "setCanceledOnTouchOutside(false)", "setCanceledOnTouchOutside(true)")

# ── 6. PushImpl → comment forceUpdate ──
for f in find("PushImpl.smali"):
    t = f.read_text("utf-8", errors="replace"); lines = t.splitlines(keepends=True)
    for i, l in enumerate(lines):
        if "forceUpdate" in l and not l.strip().startswith("#"):
            lines[i] = f"# {l}"
    f.write_text("".join(lines)); CHANGES += 1
    print(f"  COMMENT forceUpdate in {f.relative_to(APK)}")

print(f"\n=== 补丁完成: {CHANGES} 处修改 ===")
