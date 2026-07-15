#!/usr/bin/env python3
"""Hongguo v21 — Find and analyze the modder's network connection method.
Goal: find the method containing oneseeker.top URL and its network call, so we can NOP it."""
import re
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TARGET = "oneseeker.top"

found = []
for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("MainFragmentActivity.smali"):
        text = f.read_text("utf-8", errors="replace")
        lines = text.splitlines(keepends=True)

        for i, ln in enumerate(lines):
            if TARGET in ln:
                # Find method start/end
                m_start, m_name, m_end = None, None, None
                for j in range(i, -1, -1):
                    if ".method " in lines[j]:
                        m_start = j
                        m_name = lines[j].strip()
                        break
                for j in range(i, min(i + 200, len(lines))):
                    if ".end method" in lines[j]:
                        m_end = j
                        break

                print(f"=== Found '{TARGET}' in {f.relative_to(APK)}:{i+1} ===")
                print(f"Method: {m_name} (lines {m_start+1}-{(m_end or '?')})")
                print(f"\nContext:")
                for j in range(max(0, i-3), min(len(lines), i+4)):
                    marker = ">>>" if j == i else "   "
                    print(f"  {marker} {j+1}: {lines[j].rstrip()[:160]}")

                if m_start is not None:
                    # Show the method body
                    print(f"\nFull method body (lines {m_start+1}-{min(m_start+80, len(lines))}):")
                    for j in range(m_start, min(m_start + 80, len(lines))):
                        print(f"  {j+1}: {lines[j].rstrip()[:160]}")
                        if j == m_end: break

                # Find network calls in this method
                print(f"\nNetwork calls in method:")
                for j in range(m_start or 0, min(m_start or 0 + 80, len(lines))):
                    ln2 = lines[j].strip()
                    if any(x in ln2 for x in ["invoke", "HttpURL", "openConnection",
                                              "connect", "java.net.URL", "new-instance",
                                              "HttpPost", "HttpGet", "execute",
                                              "Socket", "InetAddress"]):
                        print(f"  {j+1}: {ln2[:160]}")
                found.append(f)

print(f"\n=== Analyzed {len(found)} files ===")
