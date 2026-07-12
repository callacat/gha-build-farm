#!/usr/bin/env python3
"""红果短剧 v13 — 方法级拦截：阻断包含更新关键词的整个方法"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
KEYWORDS = ["更新", "update", "升级", "version", "立即更新", "强制", "force"]
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

        in_method = False
        method_start = -1
        method_has_keyword = False

        for i, ln in enumerate(lines):
            # 检测方法开始
            if re.match(r'^\s*\.method\s+', ln):
                in_method = True
                method_start = i
                method_has_keyword = False
                continue

            # 检测方法结束
            if re.match(r'^\s*\.end method', ln):
                in_method = False
                continue

            # 在方法内检测关键词
            if in_method and not method_has_keyword:
                for kw in KEYWORDS:
                    if kw in ln:
                        method_has_keyword = True
                        # 找到第一个非注释的指令行，插入 return-void
                        for j in range(method_start + 1, i + 30):
                            if j >= len(lines):
                                break
                            # 跳过 .locals / .param / .annotation / 注释行
                            if re.match(r'^\s*(\.|#)', lines[j]):
                                continue
                            # 找到第一条指令
                            indent = re.match(r'^(\s*)', lines[j]).group(1)
                            lines[j] = f"{indent}return-void  # blocked method: contains '{kw}'\n"
                            dirty = True
                            HITS += 1
                            print(f"  {f.relative_to(APK)}:{j+1}  拦截方法 (关键词: {kw})")
                            break
                        break

        if dirty:
            f.write_text("".join(lines))
            MODS += 1

print(f"\n=== 补丁完成: {MODS} 个文件, {HITS} 个方法被拦截 ===")
