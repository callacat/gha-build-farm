#!/usr/bin/env python3
"""APK 减容 — advzip 逐条重压缩 ZIP 条目。
在 rebuild 后、zipalign 前运行，不破坏 ZIP 结构。
"""
import sys, subprocess, shutil
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if not APK or not APK.exists():
    print("  ⚠ APK 不存在，跳过")
    sys.exit(0)

before = APK.stat().st_size
tmp = APK.with_suffix('.tmp.apk')

try:
    shutil.copy2(APK, tmp)
    r = subprocess.run(['advzip', '-z', '-4', str(tmp)], capture_output=True, timeout=600)
    after = tmp.stat().st_size
    if after < before:
        shutil.move(tmp, APK)
        saved = before - after
        pct = (before - after) * 100 // before
        print(f"  🗜️ {before//1024//1024}MB → {after//1024//1024}MB (-{saved//1024//1024}MB, {pct}%)")
    else:
        tmp.unlink()
        print("  ⚠ 无压缩收益，保留原文件")
except FileNotFoundError:
    print("  ⚠ advzip 未安装，跳过")
except Exception as e:
    print(f"  ⚠ 失败: {e}")
    if tmp.exists(): tmp.unlink()
