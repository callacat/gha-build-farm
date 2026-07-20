#!/usr/bin/env python3
"""APK 减容 — 用 advzip 重新压缩 APK 的 ZIP 层。
apktool b 输出的 APK 压缩率低，advzip 可额外压缩减少 60-100MB。
在 rebuild 后、zipalign 前运行。
"""
import sys, subprocess
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if not APK or not APK.exists():
    print("  ⚠ APK 不存在，跳过")
    sys.exit(0)

before = APK.stat().st_size

# 用 advzip 重新压缩（4 = 最大压缩，重新遍历所有条目）
try:
    r = subprocess.run(
        ['advzip', '-z', '-4', str(APK)],
        capture_output=True, timeout=300
    )
    after = APK.stat().st_size
    saved = before - after
    pct = (before - after) * 100 // before
    print(f"  🗜️ {before//1024//1024}MB → {after//1024//1024}MB (-{saved//1024//1024}MB, {pct}%)")
    if r.stderr:
        print(f"  ⚠ stderr: {r.stderr.decode()[:200]}")
except FileNotFoundError:
    print("  ⚠ advzip 未安装，跳过")
except Exception as e:
    print(f"  ⚠ 失败: {e}")
