#!/usr/bin/env python3
"""红果短剧 v13 — 全局搜索"立即更新"字符串引用"""
import re
from pathlib import Path

APK = Path("/tmp/apktool_out")

# 搜索所有 smali 中的 "立即更新" / "立即升级" / "马上更新"
KEYWORDS = ["立即更新", "立即升级", "马上更新", "版本更新", "Update Now"]

hits = []
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir():
        continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        if "/androidx/" in r or "/annotation/" in r:
            continue
        try:
            t = f.read_text("utf-8", errors="replace")
        except:
            continue

        lines = t.splitlines()
        for i, ln in enumerate(lines):
            for kw in KEYWORDS:
                if kw in ln:
                    hits.append((f.relative_to(APK), i+1, ln.strip()[:120]))
                    break

if not hits:
    print("[!] No '立即更新' string found in any smali file")
    exit(0)

print(f"[✓] Found {len(hits)} references to update keywords:\n")
for path, line, content in hits[:100]:
    print(f"  {path}:{line}")
    print(f"    {content}\n")

# 输出到文件
out = Path("/tmp/update-string-refs.txt")
out.write_text("\n".join(f"{p}:{ln}\n  {c}" for p, ln, c in hits))
print(f"\n[✓] Full result saved to {out}")
