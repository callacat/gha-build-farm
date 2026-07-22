#!/usr/bin/env python3
"""APK 减容 — 用 zipalign -z（Zopfli 算法，SDK 自带，比 advzip 快得多）。
在 rebuild 后、签名前运行。
zipalign -z 4 = Zopfli 重压缩 + 4字节对齐，一步到位。
"""
import sys, subprocess, shutil
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else None
if not APK or not APK.exists():
    print("  ⚠ APK 不存在，跳过")
    sys.exit(0)

before = APK.stat().st_size
out = APK.with_suffix('.aligned.apk')

try:
    # Find zipalign in SDK
    sdk = "/usr/local/lib/android/sdk"
    bt = subprocess.run(['find', sdk, '-name', 'zipalign', '-type', 'f'], capture_output=True, text=True, timeout=5)
    zipalign = bt.stdout.strip().split('\n')[0]
    if not zipalign:
        print("  ⚠ zipalign not found")
        sys.exit(0)

    r = subprocess.run([zipalign, '-z', '4', str(APK), str(out)], capture_output=True, timeout=180)
    if out.exists():
        after = out.stat().st_size
        saved = before - after
        pct = (before - after) * 100 // before
        print(f"  🗜️ {before//1024//1024}MB → {after//1024//1024}MB (-{saved//1024//1024}MB, {pct}%)")
        shutil.move(out, APK)
    else:
        print(f"  ⚠ zipalign failed")
except Exception as e:
    print(f"  ⚠ 失败: {e}")
