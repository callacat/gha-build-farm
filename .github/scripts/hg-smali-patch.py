#!/usr/bin/env python3
"""红果短剧 去强制更新 v2 — 仅安全字符串替换，不重写方法体"""
import sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
CHANGES = 0

def patch_file(path, old, new):
    global CHANGES
    if not path.is_file(): return
    t = path.read_text("utf-8", errors="replace")
    if old not in t: return
    n = t.count(old)
    t = t.replace(old, new)
    path.write_text(t)
    CHANGES += 1
    print(f"  [{n}x] PATCH {path.relative_to(APK)}: {old[:60]}")

def find(pat):
    for sd in sorted(APK.glob("smali*")):
        if sd.is_dir():
            yield from sd.rglob(pat)

# ── 1. ForceUpdateInfo → return false for force field ──
for f in find("ForceUpdateInfo*.smali"):
    # Change const/4 vX, 0x1 (true) to const/4 vX, 0x0 (false)
    patch_file(f, "const/4 v0, 0x1", "const/4 v0, 0x0")
    patch_file(f, "const/4 v1, 0x1", "const/4 v1, 0x0")
    patch_file(f, "const/4 v2, 0x1", "const/4 v2, 0x0")

# ── 2. AppUpdateConfig → all boolean configs to false ──
for f in find("AppUpdateConfig.smali"):
    patch_file(f, "const/4 v0, 0x1", "const/4 v0, 0x0")
    patch_file(f, "const/4 v1, 0x1", "const/4 v1, 0x0")

# ── 3. IUpgradePopupNewStyle / UpgradePopupNewStyle ──
for f in find("UpgradePopupNewStyle.smali"):
    # Change show state to dismiss
    patch_file(f, "->show()", "->dismiss()")

# ── 4. setCancelable(false) → true (skip AndroidX) ──
for f in find("*.smali"):
    r = str(f.relative_to(APK))
    if "/androidx/" in r or "/android/support/" in r: continue
    patch_file(f, "setCancelable(false)", "setCancelable(true)")
    patch_file(f, "setCanceledOnTouchOutside(false)", "setCanceledOnTouchOutside(true)")

# ── 5. PopDefiner force_upgrade → const null ──
for f in find("PopDefiner*.smali"):
    patch_file(f, "->force_upgrade_dialog", "->force_upgrade_dialog_NOP")

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
    print(f"  COMMENT forceUpdate in {f.relative_to(APK)}")

# ── 7. NsUpdateServiceImpl → const false ──
for f in find("NsUpdateServiceImpl.smali"):
    patch_file(f, "const/4 v0, 0x1", "const/4 v0, 0x0")
    patch_file(f, "const/4 v1, 0x1", "const/4 v1, 0x0")

print(f"\n=== 补丁完成: {CHANGES} 处修改 ===")
