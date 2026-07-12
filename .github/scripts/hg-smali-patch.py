#!/usr/bin/env python3
"""红果短剧 v9 — 版本号注入：阻断所有更新检测"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
FAKE_VERSION = "0x5f5e100"  # 99999999
MODS = 0
HITS = 0

for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir():
        continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        if "/androidx/" in r or "/annotation/" in r:
            continue
        t = f.read_text("utf-8", errors="replace")
        lines = t.splitlines(keepends=True)
        dirty = False

        for i, ln in enumerate(lines):
            # iget vREG, vREG, Landroid/content/pm/PackageInfo;->versionCode:I
            # → const vREG, 0x5f5e100
            m = re.search(
                r'iget\s+(\{[vp\d]+\}|[vp\d]+)\s*,\s*[vp\d]+\s*,\s*Landroid/content/pm/PackageInfo;->versionCode:I',
                ln,
            )
            if not m:
                continue
            # Extract the destination register
            dst = m.group(1)
            dst = dst.strip("{}")
            indent = re.match(r'^(\s*)', ln).group(1)
            lines[i] = f"{indent}const {dst}, {FAKE_VERSION}  # versionCode → {FAKE_VERSION}\n"
            dirty = True
            HITS += 1
            print(f"  {f.relative_to(APK)}:{i+1}  versionCode → {FAKE_VERSION}")

        if dirty:
            f.write_text("".join(lines))
            MODS += 1

print(f"\n=== 补丁完成: {MODS} 个文件, {HITS} 处 versionCode 注入 ===")
