#!/usr/bin/env python3
"""红果短剧 v12 — 拦截 "立即更新" 弹窗的 show() 调用"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TARGET_TEXT = "立即更新"
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

        # 先检查文件是否包含目标字符串
        if TARGET_TEXT not in t:
            continue

        lines = t.splitlines(keepends=True)
        dirty = False

        # 找到包含 "立即更新" 的 const-string 行
        for i, ln in enumerate(lines):
            if TARGET_TEXT not in ln:
                continue
            if not re.search(r'const-string\s+[vp\d]+\s*,\s*"[^"]*' + TARGET_TEXT, ln):
                continue

            # 向下搜索 50 行内的 Dialog.show() / AlertDialog$Builder.show()
            for j in range(i, min(i + 50, len(lines))):
                m = re.search(
                    r'invoke-virtual\s+\{([vp\d]+)(?:,\s*[vp\d]+)?\}\s*,\s*L[^;]*/(?:AlertDialog\$Builder|Dialog);->show\(\)',
                    lines[j],
                )
                if not m:
                    continue
                indent = re.match(r'^(\s*)', lines[j]).group(1)
                lines[j] = f"{indent}return-void  # blocked: {TARGET_TEXT} dialog.show()\n"
                dirty = True
                HITS += 1
                print(f"  {f.relative_to(APK)}:{j+1}  拦截 show() (源自 {TARGET_TEXT})")
                break

        if dirty:
            f.write_text("".join(lines))
            MODS += 1

print(f"\n=== 补丁完成: {MODS} 个文件, {HITS} 个 show() 调用被拦截 ===")
