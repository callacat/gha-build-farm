#!/usr/bin/env python3
"""红果短剧 v11 — 精确毒化字节跳动更新/监控域名"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
POISON = "127.0.0.1"

# 从 Mihomo 日志提取的可疑域名
TARGETS = [
    "oneseeker.top",
    "171.43.214.186",
    "polaris5-normal-hl.zijieapi.com",
    "lf-normal-gr-sourcecdn.bytegecko.com",
    "idouyinvod.com",  # 泛域名
    "dig.bdurl.net",
    "gecko5-hl.zijieapi.com",
    "mon11-misc-hl.fqnovel.com",
]

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
            # const-string vREG, "https?://...target_domain..."
            for target in TARGETS:
                if target not in ln:
                    continue
                m = re.search(
                    r'const-string\s+([vp\d]+)\s*,\s*"(https?://[^"]*' + re.escape(target) + r'[^"]*)"',
                    ln,
                )
                if not m:
                    continue
                reg = m.group(1)
                url = m.group(2)
                indent = re.match(r'^(\s*)', ln).group(1)
                lines[i] = f'{indent}const-string {reg}, "http://{POISON}"  # blocked: {url[:50]}...\n'
                dirty = True
                HITS += 1
                print(f"  {f.relative_to(APK)}:{i+1}  毒化: {url[:60]}")
                break

        if dirty:
            f.write_text("".join(lines))
            MODS += 1

print(f"\n=== 补丁完成: {MODS} 个文件, {HITS} 个字节跳动域名毒化 ===")
