#!/usr/bin/env python3
"""Hongguo v21 — Find oneseeker method context and suggest NOP target."""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TARGET = "oneseeker.top"

found = []
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        if "MainFragmentActivity" not in f.name: continue
        text = f.read_text("utf-8", errors="replace")
        lines = text.splitlines(keepends=True)
        for i, ln in enumerate(lines):
            if TARGET not in ln: continue
            # Method start: walk backwards
            m_start, m_name = None, None
            for j in range(i, -1, -1):
                s = lines[j].strip()
                if s.startswith(".method "):
                    m_start, m_name = j, s
                    break
            # Method end: walk forwards
            m_end = None
            for j in range(i, min(i + 200, len(lines))):
                if ".end method" in lines[j]:
                    m_end = j
                    break
            if m_start is None: continue

            print(f"=== {f.relative_to(APK)}:{i+1} ===")
            print(f"Method ({m_start+1}-{m_end+1}): {m_name}")

            # Show the register that holds the URL and trace it
            reg = None
            m2 = re.search(r'const-string\s+([vp]\d+)\s*,\s*"[^"]*oneseeker', ln)
            if m2: reg = m2.group(1)
            print(f"URL register: {reg}")

            # Show full method body for analysis
            end = min(m_end, m_start + 60) if m_end else min(m_start + 60, len(lines))
            for j in range(m_start, end):
                ln2 = lines[j].rstrip()
                marker = ">>>" if j == i else ("   " if abs(j - i) > 3 else "  !")
                if j == m_start or abs(j - i) <= 3:
                    print(f"  {marker} {j+1}: {ln2[:180]}")
                elif "invoke" in ln2 and reg and reg in ln2:
                    print(f"  [NET] {j+1}: {ln2[:180]}")
                elif j == m_end:
                    print(f"  {marker} {j+1}: {ln2[:180]}")
            if m_end and m_end >= m_start + 60:
                print(f"  ... ({m_end - m_start - 60} more lines)")
            print()
            found.append(f)

print(f"=== Analyzed {len(found)} files ===")
