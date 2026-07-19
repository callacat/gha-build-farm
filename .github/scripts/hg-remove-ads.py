#!/usr/bin/env python3
"""Fix network config — the smali method stub replaces the old directory-delete approach.
   Kept as a lightweight prep step for hg-smali-stub.py."""

from __future__ import annotations
import argparse, json, sys
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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

    print("=== Fix network config ===")
    fix_network_security_config(source)

    print("\n✓ done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
