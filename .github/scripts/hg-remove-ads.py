#!/usr/bin/env python3
"""按精确包名找到 smali 类并 stub 方法体。不删文件，不崩溃。"""

from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _stub_method_body(method_lines: list[str]) -> str:
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


def stub_package_classes(source: Path, packages: list[str]) -> int:
    """按精确 smali 包路径找到类文件，stub 其所有方法体。

    不删文件，只替换方法体为最小桩。
    """
    count = 0
    target_methods = ["onCreateView", "onViewCreated", "onCreate", "onActivityCreated",
                      "initView", "initData", "init", "loadAd", "showAd", "onBindViewHolder"]

    for smali_dir in sorted(source.glob("smali*")):
        if not smali_dir.is_dir():
            continue
        for pkg in packages:
            pkg_dir = smali_dir / pkg
            if not pkg_dir.exists():
                continue
            for smali_file in sorted(pkg_dir.rglob("*.smali")):
                try:
                    lines = smali_file.read_text(encoding="utf-8").split("\n")
                except Exception:
                    continue

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
                        if any(n in method_sig for n in target_methods):
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
                    # 确认是 Fragment/View 类（有超类声明）
                    is_relevant = any("Fragment" in l or "View" in l or "Adapter" in l or "Activity" in l
                                      for l in lines if ".super" in l)
                    if not is_relevant:
                        continue
                    smali_file.write_text("\n".join(out), encoding="utf-8")
                    class_match = re.search(r'\.class\s+\S+\s+(L[\w/$-]+;)', "\n".join(lines[:5]))
                    cls = class_match.group(1) if class_match else "?"
                    count += 1
                    rel = str(smali_file.relative_to(source))
                    print(f"  ✓ stub {rel}")

    return count


def fix_network_security_config(source: Path) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--ad-config", required=True)
    args = parser.parse_args()

    source = Path(args.source)
    config = load_json(args.ad_config)

    print("=== Phase 1: 修复网络配置 ===")
    fix_network_security_config(source)

    print("\n=== Phase 2: Stub 目标包 ===")
    packages = config.get("packages_to_stub", [])
    if packages:
        n = stub_package_classes(source, packages)
        print(f"  → 处理 {n} 个类文件")
    else:
        print("  (跳过)")

    print("\n✓ 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
