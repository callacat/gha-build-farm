#!/usr/bin/env python3
import sys
"""NOP the method containing oneseeker.top - runs BEFORE domain poison."""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0

for f in sorted(APK.rglob("*.smali")):
    text = f.read_text("utf-8", errors="replace")
    if "oneseeker.top" not in text and "remote.oneseeker.top" not in text and "dongle.oneseeker.top" not in text:
        continue

    print(f"=== Found oneseeker in {f.relative_to(APK)} ===")
    lines = text.splitlines(keepends=True)

    # Find URL line
    url_idx = None
    for i, ln in enumerate(lines):
        if "oneseeker.top" in ln:
            url_idx = i
            break

    # Walk backwards to find .method
    m_start, m_name = None, None
    for i in range(url_idx, -1, -1):
        if lines[i].strip().startswith(".method "):
            m_start, m_name = i, lines[i].strip()
            break

    if m_start is None:
        print("  [FAIL] No .method found above URL"); continue

    # Walk forwards to find .end method
    depth = 0
    m_end = None
    for i in range(m_start + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith(".method "):
            depth += 1
        elif stripped.startswith(".end method"):
            if depth == 0:
                m_end = i
                break
            depth -= 1

    if m_end is None:
        print("  [FAIL] No .end method found"); continue

    # Extract return type from method signature: grab everything after last ')'
    paren_idx = m_name.rfind(")")
    ret_type = m_name[paren_idx + 1:].strip() if paren_idx > 0 else "V"
    # smali return types can have trailing ";" for object types
    ret_type = ret_type.rstrip(";")

    print(f"  Method ({m_start+1}-{m_end+1}): {m_name}")
    print(f"  Return type: {ret_type}")

    # NOP the method body: keep original .end method in place
    header = lines[:m_start + 1]
    if ret_type == "V":
        body = ["    .locals 0\n", "    return-void  # oneseeker disabled\n"]
    elif ret_type in ("L",) or ret_type.startswith("L") or ret_type.startswith("["):
        body = ["    .locals 1\n", "    const/4 v0, 0x0\n", "    return-object v0  # null\n"]
    elif ret_type in ("J", "D"):
        body = ["    .locals 2\n", "    const-wide/16 v0, 0x0\n", "    return-wide v0  # disabled\n"]
    else:
        body = ["    .locals 1\n", "    const/4 v0, 0x0\n", "    return v0  # disabled\n"]
    # Keep original .end method line — body does NOT include .end method
    footer = lines[m_end:]

    new_text = "".join(header + body + footer)
    f.write_text(new_text, encoding="utf-8")
    MODS += 1
    print(f"  ✅ NOPped -> {'void' if ret_type == 'V' else 'null/false'}")
    break

print(f"\n=== Done: {MODS} files patched ===")
