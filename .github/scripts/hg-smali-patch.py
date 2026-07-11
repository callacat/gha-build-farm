#!/usr/bin/env python3
"""红果短剧 去强制更新 v5 — 先分析再打补丁"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
CHANGES = 0

def find(pat):
    for sd in sorted(APK.glob("smali*")):
        if sd.is_dir():
            yield from sd.rglob(pat)

# ═══ 第一步：诊断 ═══
print("=== DIAGNOSTIC: SplashActivity smali ===")
for f in find("SplashActivity.smali"):
    r = str(f.relative_to(APK))
    t = f.read_text("utf-8", errors="replace")
    # Check if it's the app's SplashActivity
    lines = t.splitlines()
    for i, l in enumerate(lines):
        # find all method calls that could be the trigger
        ls = l.strip()
        if "startActivity" in ls or "Intent" in ls or "ACTION_VIEW" in ls:
            print(f"  {f.relative_to(APK)}:L{i+1} {ls[:120]}")
        if "dialog" in ls.lower() or "finish" in ls.lower() or "onCreate" in ls:
            if not ls.startswith('.') and ls:
                print(f"  {f.relative_to(APK)}:L{i+1} {ls[:120]}")

# ═══ 第二步：找到后打补丁 ═══
# Also check MainFragmentActivity
print("\n=== DIAGNOSTIC: MainFragmentActivity ===")
for f in find("MainFragmentActivity.smali"):
    t = f.read_text("utf-8", errors="replace")
    for i, l in enumerate(t.splitlines()):
        ls = l.strip()
        if "startActivity" in ls or "ACTION_VIEW" in ls or "dialog" in ls.lower():
            if "androidx" not in str(f.relative_to(APK)):
                print(f"  L{i+1} {ls[:120]}")

# ═══ 第三步：搜索所有含 update/download URL 的 smali ═══
print("\n=== DIAGNOSTIC: Ali/Pay/Taobao/Weibo URL references ===")
for f in find("*.smali"):
    t = f.read_text("utf-8", errors="replace")
    for kw in ["taobao", "weibo.com", "weixin.qq", "xiaohongshu", "alipay"]:
        if kw in t.lower():
            r = str(f.relative_to(APK))
            if "androidx" not in r:
                print(f"  {r}: {kw}")
                for m, l in enumerate(t.splitlines()):
                    if kw in l.lower():
                        print(f"    L{m+1}: {l.strip()[:120]}")

# ═══ 第四步：设置安全补丁（已有的大部分） ═══
def replace_in(path, old, new):
    global CHANGES
    if not path.is_file(): return
    t = path.read_text("utf-8", errors="replace")
    if old not in t: return
    t = t.replace(old, new)
    path.write_text(t)
    CHANGES += 1
    print(f"  PATCH {path.relative_to(APK)}")

# setCancelable
for f in find("*.smali"):
    r = str(f.relative_to(APK))
    if "/androidx/" in r or "/android/support/" in r: continue
    replace_in(f, "setCancelable(false)", "setCancelable(true)")
    replace_in(f, "setCanceledOnTouchOutside(false)", "setCanceledOnTouchOutside(true)")

# PopDefiner upgrade/update/force dialogs
for f in find("PopDefiner*.smali"):
    t = f.read_text("utf-8", errors="replace"); o = t
    t = re.sub(r'sget-object\s+(\w+),\s*Lcom/dragon/read/pop/PopDefiner;->(\w*(?:upgrade|update|force)\w*):.*',
               r'const/4 \1, 0x0  # \2 NOP', t)
    if t != o:
        f.write_text(t); CHANGES += 1
        print(f"  NOP force dialogs in {f.relative_to(APK)}")

# UpgradePopupNewStyle
for f in find("UpgradePopupNewStyle*.smali"):
    replace_in(f, "->show()Z", "->dismiss()V")
    replace_in(f, "->show()V", "->dismiss()V")

# PushImpl
for f in find("PushImpl.smali"):
    t = f.read_text("utf-8", errors="replace"); lines = t.splitlines(keepends=True)
    for i, l in enumerate(lines):
        if "forceUpdate" in l and not l.strip().startswith("#"):
            lines[i] = f"# {l}"
    f.write_text("".join(lines)); CHANGES += 1
    print(f"  COMMENT forceUpdate in {f.relative_to(APK)}")

print(f"\n=== 补丁完成: {CHANGES} 处修改 ===")
