#!/usr/bin/env python3
"""仅删除指定包目录，不做 smali 编辑。"""

from __future__ import annotations
import argparse, json, shutil, sys
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def delete_packages(source: Path, packages: list[str]) -> int:
    count = 0
    for smali_dir in sorted(source.glob("smali*")):
        if not smali_dir.is_dir():
            continue
        for pkg in packages:
            target = smali_dir / pkg
            if target.exists():
                try:
                    target.resolve().relative_to(source.resolve())
                except ValueError:
                    continue
                shutil.rmtree(target)
                count += 1
                print(f"  ✓ rm {target.relative_to(source)}")
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
        print(f"  ✓ fix {xml_file.relative_to(source)}")
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--ad-config", required=True)
    args = parser.parse_args()

    source = Path(args.source)
    config = load_json(args.ad_config)

    print("=== Fix network config ===")
    fix_network_security_config(source)

    print("\n=== Delete packages ===")
    packages = config.get("packages_to_delete", [])
    if packages:
        n = delete_packages(source, packages)
        print(f"  → deleted {n} directories")
    else:
        print("  (empty)")

    print("\n✓ done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
