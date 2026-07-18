#!/usr/bin/env python3
"""仅在 smali 中搜索并 stub Fragment（商城/赚钱等页面），不删任何 SDK 包。"""

from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _stub_method_body(method_lines: list[str]) -> str:
    """将 smali 方法体替换为最小桩代码，根据返回类型选正确指令。"""
    first = method_lines[0]
    if ")Landroid/view/View;" in first:
        stub = "    .registers 1\n    const/4 v0, 0x0\n    return-object v0"
    elif ")V" in first:
        stub = "    .registers 1\n    return-void"
    elif ")Z" in first:
        stub = "    .registers 1\n    const/4 v0, 0x0\n    return v0"
    elif ")I" in first:
        stub = "    .registers 1\n    const/4 v0, 0x0\n    return v0"
    elif ")J" in first:
        stub = "    .registers 2\n    const-wide/16 v0, 0x0\n    return-wide v0"
    else:
        stub = "    .registers 1\n    return-void"
    return f"{first}\n{stub}\n.end method"


def stub_fragment_pages(source: Path, keywords: list[str]) -> int:
    """在 smali 中搜索 const-string 含关键词的 Fragment 类，stub 其方法体。"""
    count = 0
    processed: set[str] = set()

    for smali_dir in sorted(source.glob("smali*")):
        if not smali_dir.is_dir():
            continue
        for smali_file in sorted(smali_dir.rglob("*.smali")):
            try:
                content = smali_file.read_text(encoding="utf-8")
            except Exception:
                continue

            if not any(kw in content for kw in keywords):
                continue

            class_match = re.search(r'\.class\s+\S+\s+(L[\w/$-]+;)', content)
            if not class_match:
                continue
            class_desc = class_match.group(1)
            if class_desc in processed:
                continue

            lines = content.split("\n")
            if not any(
                line.strip().startswith("const-string") and any(kw in line for kw in keywords)
                for line in lines
            ):
                continue

            # 检查是不是 Fragment
            is_fragment = any("Fragment" in line for line in lines if ".super" in line)
            if not is_fragment:
                continue

            processed.add(class_desc)
            rel = safe_relative(smali_file, source)
            if not rel.startswith("smali") or "android/support" in rel or "androidx" in rel:
                continue

            # stub 关键方法
            out: list[str] = []
            i = 0
            modified = False
            while i < len(lines):
                stripped = lines[i].strip()
                if stripped.startswith(".method "):
                    method_lines = [lines[i]]
                    j = i + 1
                    while j < len(lines) and lines[j].strip() != ".end method":
                        method_lines.append(lines[j])
                        j += 1
                    end_line = lines[j] if j < len(lines) else ".end method"

                    method_sig = " ".join(stripped.split()[:3])
                    # 只 stub 生命周期方法和初始化方法
                    if any(n in method_sig for n in (
                        "onCreateView", "onViewCreated", "onActivityCreated",
                        "onCreate", "initView", "initData"
                    )):
                        out.append(_stub_method_body(method_lines))
                        modified = True
                        i = j + 1
                        continue
                    out.extend(method_lines)
                    out.append(end_line)
                else:
                    out.append(lines[i])
                i += 1

            if modified:
                smali_file.write_text("\n".join(out), encoding="utf-8")
                count += 1
                print(f"  ✓ stub {rel}: {class_desc}")

    return count


def fix_network_security_config(source: Path) -> None:
    """替换 network_security_config.xml 为简化版。"""
    for xml_file in source.rglob("network_security_config.xml"):
        simplified = '''<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
</network-security-config>'''
        xml_file.write_text(simplified, encoding="utf-8")
        print(f"  ✓ 简化 {xml_file.relative_to(source)}")
        return


def safe_relative(path: Path, anchor: Path) -> str:
    try:
        return str(path.relative_to(anchor))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stub ad/mall fragments in smali")
    parser.add_argument("--source", required=True)
    parser.add_argument("--ad-config", required=True)
    args = parser.parse_args()

    source = Path(args.source)
    config = load_json(args.ad_config)

    print("=== Phase 1: 修复网络配置 ===")
    fix_network_security_config(source)

    print("\n=== Phase 2: Stub Fragment 页面 ===")
    keywords = config.get("fragment_keywords", [])
    if keywords:
        n = stub_fragment_pages(source, keywords)
        print(f"  → 处理 {n} 个 Fragment")
    else:
        print("  (跳过)")

    print("\n✓ 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
