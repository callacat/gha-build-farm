#!/usr/bin/env python3
"""终极搜索：找出所有自定义 URL 字符串的 smali 文件 — 黑产代码就藏在那里"""
import re
from pathlib import Path

APKTOOL = Path("/tmp/apktool_out/")

# 已知 SDK URL 白名单（排除这些）
KNOWN_SDK = [
    "google", "android", "w3.org", "xmlpull", "github", "fqnovel", "snssdk",
    "bytedance", "zijieapi", "pstatp", "byteimg", "schemas", "maven", "apache",
    "gradle", "spring", "kotlin", "coroutine", "okhttp", "retrofit", "lynx",
    "bytegecko", "bytecdn", "bdurl", "toutiao", "amemv", "douyin", "pangle",
    "alipay", "weibo", "weixin", "taobao", "xiaohongshu", "openmobile",
    "developer", "byteoversea", "bytedns", "novelquickapp"
]

# 搜索所有 smali 中的 URL 字符串
print("=== 非 SDK URL（可能是黑产下载地址）===")
for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        t = f.read_text("utf-8", errors="replace")
        urls = re.findall(r'https?://[a-zA-Z0-9./_-]+', t)
        for u in urls:
            if not any(k in u.lower() for k in KNOWN_SDK):
                r = str(f.relative_to(APKTOOL))
                print(f"  URL: {u}")
                print(f"  FILE: {r}")
                # Print surrounding context
                idx = t.find(u)
                start = max(0, t.rfind('\n', 0, idx) - 150)
                end = min(len(t), t.find('\n', idx) + 1)
                ctx = t[start:end].strip()
                print(f"  CTX: ...{ctx[-120:]}")
                print()

# 搜索夸克/下载相关字符串
print("=== 'quark' / '夸克' / '立即更新' / 'cashdesk' / 'pan' / '网盘' ===")
for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        t = f.read_text("utf-8", errors="replace")
        for kw in ["quark", "夸克", "cashdesk", "立即更新", "立即升级", "网盘", "pan.baidu", "lanzou", "ct.ghpym"]:
            if kw in t.lower():
                r = str(f.relative_to(APKTOOL))
                for i, l in enumerate(t.splitlines()):
                    if kw in l.lower():
                        print(f"  FILE: {r} L{i+1}")
                        print(f"    {l.strip()[:150]}")
print("=== 搜索结束 ===")
