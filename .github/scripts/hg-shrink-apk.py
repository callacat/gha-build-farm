#!/usr/bin/env python3
"""APK 减容 — 重打包后用 7zip 重新压缩 ZIP 层。
apktool b 输出压缩率低，7z -mx=9 可压到接近原版大小。
在 rebuild 后、zipalign 前运行。
"""
import sys, subprocess, shutil
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if not APK or not APK.exists():
    print("  ⚠ APK 不存在，跳过")
    sys.exit(0)

before = APK.stat().st_size
tmp = APK.with_suffix('.7z.tmp')

try:
    # 7z a -mx=9 -tzip recompress
    r = subprocess.run(
        ['7z', 'a', '-mx=9', '-tzip', '-bb0', '-y', str(tmp), str(APK)],
        capture_output=True, timeout=600
    )
    if tmp.exists() and tmp.stat().st_size > 0:
        shutil.move(tmp, APK)
        after = APK.stat().st_size
        saved = before - after
        pct = (before - after) * 100 // before
        print(f"  🗜️ {before//1024//1024}MB → {after//1024//1024}MB (-{saved//1024//1024}MB, {pct}%)")
    else:
        print(f"  ⚠ 压缩后文件异常，保留原文件")
        if tmp.exists(): tmp.unlink()
except Exception as e:
    print(f"  ⚠ 压缩失败: {e}")
    if tmp.exists(): tmp.unlink()
