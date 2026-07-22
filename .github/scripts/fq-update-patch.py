#!/usr/bin/env python3
"""Fanqie 番茄小说 — Pangle (穿山甲) 更新弹窗屏蔽
基于分析结果: LuckyDogLowUpdateDialog, GeckoClient.checkUpdateMulti, forceUpdate
"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

# 1. Manifest: 移除或禁用 LuckyDogLowUpdateDialog activity
print("=== Phase 1: Manifest - 禁用 LuckyDogLowUpdateDialog ===")
manifest = APK / "AndroidManifest.xml"
if manifest.exists():
    text = manifest.read_text("utf-8", errors="replace")
    # 找到 LuckyDogLowUpdateDialog activity 并添加 android:enabled="false"
    pattern = r'(<activity\s+android:name="com\.bytedance\.ug\.sdk\.luckydog\.window\.dialog\.LuckyDogLowUpdateDialog"[^>]*)>'
    def repl(m):
        attrs = m.group(1)
        if 'android:enabled="false"' not in attrs:
            return attrs + ' android:enabled="false">'
        return m.group(0)
    new_text = re.sub(pattern, repl, text)
    if new_text != text:
        manifest.write_text(new_text, encoding="utf-8")
        print(f"  ✅ Manifest: added android:enabled=\"false\" to LuckyDogLowUpdateDialog")
        TOTAL += 1
    else:
        print(f"  (already disabled or already modified)

# 2. smali_classes10/uo4/k0.smali - NOP GeckoClient.checkUpdateMulti()
print("\n=== Phase 2: GeckoClient.checkUpdateMulti() NOP ===")
gecko_files = list(APK.glob("smali*/**/uo4/k0.smali"))
for f in gecko_files:
    r = str(f.relative_to(APK))
    text = f.read_text("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    dirty = False
    for i, ln in enumerate(lines):
        if "GeckoClient;->checkUpdateMulti" in ln and "invoke-" in ln:
            indent = re.match(r"^(\s*)", ln).group(1)
            lines[i] = f"{indent}nop  # NOP GeckoClient.checkUpdateMulti\n"
            dirty = True
            TOTAL += 1
            print(f"  ✅ {r}:{i+1}")
    if dirty:
        f.write_text("".join(lines), encoding="utf-8")

# 3. forceUpdate 相关 smali 文件
print("\n=== Phase 3: forceUpdate 逻辑 NOP ===")
force_patterns = [
    ("m1.smali", "com/dragon/read/reader/utils/m1.smali"),
    ("zk4/b.smali", "zk4/b.smali"),
]
for name, path_pattern in force_patterns:
    files = list(APK.glob(f"smali*/**/{path_pattern}"))
    for f in files:
        r = str(f.relative_to(APK))
        text = f.read_text("utf-8", errors="replace")
        lines = text.splitlines(keepends=True)
        dirty = False
        for i, ln in enumerate(lines):
            # NOP forceUpdate 相关的 const/if 判断和方法调用
            if "forceUpdate" in ln.lower() and ("const" in ln or "if-" in ln or "invoke-" in ln):
                indent = re.match(r"^(\s*)", ln).group(1)
                lines[i] = f"{indent}nop  # NOP forceUpdate\n"
                dirty = True
                TOTAL += 1
                print(f"  ✅ {r}:{i+1} {ln.strip()[:60]}")
        if dirty:
            f.write_text("".join(lines), encoding="utf-8")

print(f"\n=== Done: {TOTAL} patches applied ===")