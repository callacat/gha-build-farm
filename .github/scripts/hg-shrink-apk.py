#!/usr/bin/env python3
"""红果短剧 APK 减容 — 只删安全的大文件
在 apktool rebuild 前运行，只删 assets/liborgapk.so。
不碰 smali 代码（xbridge 等是核心依赖）。
"""
import sys
from pathlib import Path

APK_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
SAVED = 0

def delete(path, desc=""):
    global SAVED
    if path.is_file():
        s = path.stat().st_size
        path.unlink()
        SAVED += s
        print(f"  🗑️ {desc or path.name} (-{s//1024//1024}MB)")
    elif path.is_dir():
        s = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        import shutil; shutil.rmtree(path)
        SAVED += s
        print(f"  🗑️ {desc or path.name} (-{s//1024//1024}MB)")

print("=== APK 减容 ===")
delete(APK_DIR / "assets" / "liborgapk.so", "Pangle 插件框架 (125MB)")
print(f"\n=== 减容完成: 节省 {SAVED//1024//1024} MB ===")
