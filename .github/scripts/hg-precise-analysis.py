#!/usr/bin/env python3
"""精准定位：提取关键更新弹窗 Java 源码"""
import re, sys, os
from pathlib import Path

JADX = Path("/tmp/jadx_out/")
APKTOOL = Path("/tmp/apktool_out/")

# 关键靶点名单
TARGETS = [
    "com/tw.java",
    "od/b.java",
    "com/dragon/read/component/biz/impl/update/NsUpdateServiceImpl.java",
    "com/dragon/read/component/biz/impl/update/UpgradePopupNewStyle.java",
    "com/dragon/read/component/biz/impl/update/AppUpdateConfig.java",
    "com/dragon/read/component/biz/impl/update/IUpgradePopupNewStyle.java",
    "com/dragon/read/rpc/model/ForceUpdateInfo.java",
    "com/dragon/read/rpc/model/ForceUpdateInfoResponse.java",
    "com/ss/android/update/UpdateService.java",
    "com/ss/android/update/UpdateDialogStyle.java",
    "com/bytedance/ug/sdk/luckydog/window/dialog/LuckyDogLowUpdateDialog.java",
    "com/dragon/read/pop/PopDefiner.java",
]

# 1. 提取 Java 源码
for target in TARGETS:
    found = list(JADX.rglob(target.split("/")[-1]))
    for f in found:
        r = str(f.relative_to(JADX))
        if target.replace(".java", "") in r.replace(".java", "").replace("$", "."):
            print(f"\n{'='*60}")
            print(f"FILE: {r}")
            print(f"{'='*60}")
            code = f.read_text("utf-8", errors="replace")
            lines = code.splitlines()
            # Print first 60 lines to identify
            for i, l in enumerate(lines[:80]):
                print(f"  L{i+1}: {l[:200]}")
            if len(lines) > 80:
                print(f"  ... ({len(lines)} total lines)")
                # Print last 20
                for i, l in enumerate(lines[-20:], len(lines)-20):
                    print(f"  L{i+1}: {l[:200]}")

# 2. 从 smali 找谁调用 UpgradePopupNewStyle.show()
print(f"\n{'='*60}")
print("CALLERS OF UpgradePopupNewStyle.smali show/init")
print(f"{'='*60}")
for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APKTOOL))
        if "androidx/" in r: continue
        t = f.read_text("utf-8", errors="replace")
        if "UpgradePopupNewStyle" in t:
            lines = t.splitlines()
            prev = ""
            for i, l in enumerate(lines):
                if "UpgradePopupNewStyle" in l:
                    print(f"  {r}:L{i+1}")
                    print(f"    {prev[:100]}")
                    print(f"    {l.strip()[:100]}")
                prev = l.strip()
