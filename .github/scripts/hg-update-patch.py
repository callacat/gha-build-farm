#!/usr/bin/env python3
"""Hongguo 弹窗屏蔽 — 基于 7月15日成功经验的增强版
策略：清空硬编码域名 + 搜所有 smali_classes 目录的 InsertScreenView NOP

Usage: python3 hg-update-patch.py /tmp/apktool_out
"""
import re, sys, subprocess
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

# Phase 1: 域名清空（7月15日成功方案）
print("=== Phase 1: 清空已知后门域名 ===")
subprocess.run([sys.executable, str(Path(__file__).parent / "hg-plan-b.py"), str(APK)])

# Phase 2: 在所有 smali_classesN 搜 InsertScreenView NOP
print("\n=== Phase 2: InsertScreenView.showView() ===")
for f in sorted(APK.rglob("InsertScreenView.smali")):
    r = str(f.relative_to(APK))
    text = f.read_text("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    dirty = False
    for i, ln in enumerate(lines):
        if "AlertDialog;->show()V" in ln:
            indent = re.match(r"^(\s*)", ln).group(1)
            lines[i] = f"{indent}nop\n"
            dirty = True; TOTAL += 1
            print(f"  ✅ {r}:{i+1}")
    if dirty:
        f.write_text("".join(lines), encoding="utf-8")

print(f"\n=== Done: {TOTAL} patches ===")
