#!/usr/bin/env python3
"""搜索第三方弹窗（鹿属软件使用声明 / 邀请加入群聊弹窗）的所有位置"""
import re
from pathlib import Path

APKTOOL = Path("/tmp/apktool_out/")

# 鹿属弹窗关键词
KEYWORDS = [
    "软件使用声明",
    "加入交流群",
    "同意且不再显示",
    "不同意",
    "鹿属",
    "使用声明",
    "不再显示",
    "交流群",
]

# 搜索 smali
print("=== 1. smali 搜索 ===")
smali_matches = []
for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir():
        continue
    for f in sd.rglob("*.smali"):
        try:
            t = f.read_text("utf-8", errors="replace")
            for kw in KEYWORDS:
                if kw in t:
                    rel = str(f.relative_to(APKTOOL))
                    # 提取包含关键词的行
                    for i, line in enumerate(t.splitlines(), 1):
                        if kw in line:
                            smali_matches.append((rel, i, kw, line.strip()[:200]))
                            print(f"  {rel}:{i}  [{kw}]")
                            print(f"    {line.strip()[:200]}")
        except Exception:
            continue

# 搜索 resources.arsc 中的字符串
print("\n=== 2. resources.xml 搜索 ===")
res_matches = []
xml_files = list(APKTOOL.glob("res/values*/strings*.xml")) + list(APKTOOL.glob("res/values*/arrays*.xml"))
for f in xml_files:
    try:
        t = f.read_text("utf-8", errors="replace")
        for kw in KEYWORDS:
            if kw in t:
                rel = str(f.relative_to(APKTOOL))
                # 提取包含关键词的 <string> 行
                for i, line in enumerate(t.splitlines(), 1):
                    if kw in line:
                        res_matches.append((rel, i, kw, line.strip()[:200]))
                        print(f"  {rel}:{i}  [{kw}]")
                        print(f"    {line.strip()[:200]}")
    except Exception:
        continue

# 搜索所有 XML layout/drawable
print("\n=== 3. layout/drawable XML 搜索 ===")
xml_all = list(APKTOOL.glob("res/layout*/*.xml")) + list(APKTOOL.glob("res/drawable*/*.xml"))
for f in xml_all:
    try:
        t = f.read_text("utf-8", errors="replace")
        for kw in KEYWORDS:
            if kw in t:
                rel = str(f.relative_to(APKTOOL))
                print(f"  {rel}  [{kw}]")
    except Exception:
        continue

# 搜索 assets/
print("\n=== 4. assets 搜索 ===")
assets_dir = APKTOOL / "assets"
if assets_dir.is_dir():
    for f in assets_dir.rglob("*"):
        if f.suffix in (".json", ".html", ".js", ".txt", ".xml", ".properties", ".cfg"):
            try:
                t = f.read_text("utf-8", errors="replace")
                for kw in KEYWORDS:
                    if kw in t:
                        rel = str(f.relative_to(APKTOOL))
                        print(f"  {rel}  [{kw}]")
            except Exception:
                continue

# 搜索 SharedPreferences 默认值（"同意且不再显示"可能有默认值）
print("\n=== 5. SharedPreferences 默认值搜索 ===")
xml_prefs = list(APKTOOL.glob("res/xml*/*.xml"))
for f in xml_prefs:
    try:
        t = f.read_text("utf-8", errors="replace")
        for kw in KEYWORDS:
            if kw in t:
                rel = str(f.relative_to(APKTOOL))
                print(f"  {rel}  [{kw}]")
    except Exception:
        continue

# 搜索 strings.xml 中的"不再显示"类 SharedPreferences key
print("\n=== 6. 常见 Dialog 触发模式 ===")
for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir():
        continue
    for f in sd.rglob("*.smali"):
        try:
            t = f.read_text("utf-8", errors="replace")
            # 找 AlertDialog + dialog.show 模式
            if "AlertDialog" in t and ("dialog.show" in t or ".show()" in t):
                if "setPositiveButton" in t or "setNegativeButton" in t:
                    rel = str(f.relative_to(APKTOOL))
                    # 检查是否包含自定义文字（排除 SDK）
                    has_custom = False
                    for kw in ["鹿属", "声明", "群", "同意", "不再"]:
                        if kw in t:
                            has_custom = True
                            break
                    if has_custom:
                        print(f"  [AlertDialog + 自定义按钮] {rel}")
        except Exception:
            continue

print(f"\n=== 汇总 ===")
print(f"  smali 匹配: {len(smali_matches)} 处")
print(f"  XML 资源匹配: {len(res_matches)} 处")
if smali_matches:
    print("\n=== 关键 smali 文件（需重点分析）===")
    files = sorted(set(m[0] for m in smali_matches))
    for f in files:
        print(f"  {f}")
