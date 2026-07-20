#!/usr/bin/env python3
"""红果短剧 APK 减容 — 删除无用大文件
在 apktool 重打包后运行，删除不影响功能的超大文件。
"""
import sys, shutil
from pathlib import Path

APK_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
SAVED = 0

# 目标：删掉这些相对路径（以 apktool_out 为根）
TARGETS = [
    # 穿山甲插件框架（125MB）：广告已拦，不需要动态下载广告插件
    "assets/liborgapk.so",

    # Slardar 监控 SDK（可能的上报模块）
    "assets/webview_monitor_js_file/slardar_sdk.js",
    "assets/webview_monitor_js_file/slardar_bridge.js",

    # 穿山甲 bridge 桥接代码（非广告不需要）
    "com/bytedance/sdk/xbridge",

    # CJPay 相关大文件（如果有）
]

def delete_if_exists(path):
    global SAVED
    if path.is_file():
        size = path.stat().st_size
        path.unlink()
        SAVED += size
        print(f"  🗑️ {path.relative_to(APK_DIR)} (-{size//1024}KB)")
    elif path.is_dir():
        size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        shutil.rmtree(path)
        SAVED += size
        print(f"  🗑️ {path.relative_to(APK_DIR)} (-{size//1024}KB)")

print("=== APK 减容 ===")

# assets/liborgapk.so
delete_if_exists(APK_DIR / "assets" / "liborgapk.so")

# smali 中穿山甲 xbridge 桥接
for smali_dir in sorted(APK_DIR.glob("smali*")):
    delete_if_exists(smali_dir / "com" / "bytedance" / "sdk" / "xbridge")

# slardar 监控 JS
delete_if_exists(APK_DIR / "assets" / "webview_monitor_js_file" / "slardar_sdk.js")
delete_if_exists(APK_DIR / "assets" / "webview_monitor_js_file" / "slardar_bridge.js")

print(f"\n=== 减容完成: 节省 {SAVED//1024//1024} MB ===")
