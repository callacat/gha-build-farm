#!/usr/bin/env python3
"""红果短剧 v12 — 定位强制更新弹窗构建代码"""
import re
from pathlib import Path

APK = Path("/tmp/apktool_out")

# 已知更新 URL 位置
TARGET_FILE = APK / "smali_classes30/com/dragon/read/pages/main/MainFragmentActivity.smali"

if not TARGET_FILE.exists():
    print(f"[!] {TARGET_FILE} not found")
    exit(1)

lines = TARGET_FILE.read_text("utf-8", errors="replace").splitlines()

# 找到 oneseeker.top/appUpdate 行号
update_url_line = None
for i, ln in enumerate(lines):
    if "oneseeker.top/appUpdate" in ln or "127.0.0.1" in ln:
        update_url_line = i
        print(f"[✓] Update URL at line {i+1}: {ln.strip()[:80]}")
        break

if not update_url_line:
    print("[!] Update URL not found in MainFragmentActivity.smali")
    exit(1)

# 向下搜索 1000 行，找 AlertDialog / Dialog 构建
dialog_patterns = [
    r'AlertDialog\$Builder',
    r'\.setTitle',
    r'\.setMessage',
    r'\.setPositiveButton',
    r'\.setNegativeButton',
    r'\.setCancelable',
    r'\.show\(\)',
]

print(f"\n=== Search AlertDialog construction within next 1000 lines ===")
hits = []
for i in range(update_url_line, min(update_url_line + 1000, len(lines))):
    ln = lines[i]
    for pat in dialog_patterns:
        if re.search(pat, ln):
            hits.append((i, ln.strip()))
            break

if not hits:
    print("[!] No AlertDialog construction found")
    exit(0)

print(f"[✓] Found {len(hits)} dialog-related lines:\n")
for line_no, content in hits[:50]:
    print(f"  {line_no+1:6d}: {content[:100]}")

# 输出到文件供后续分析
out = Path("/tmp/dialog-construction.txt")
out.write_text("\n".join(f"{ln+1:6d}: {content}" for ln, content in hits))
print(f"\n[✓] Full result saved to {out}")
