#!/usr/bin/env python3
"""Hongguo v22 — NOP the modder's network call entirely.

com/iC.smali contains oneseeker.top URL. The method that calls it
makes a synchronous HTTP request. NOP that method to skip network check.

After NOP: app never connects to oneseeker.top → no hang + no dialog.
"""
from pathlib import Path
import re

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0

# Multiple possible obfuscated class names (ic, iC, IC, etc)
for smali_dir in sorted(APK.glob("smali*")):
    if not smali_dir.is_dir():
        continue
    for f in smali_dir.rglob("*.smali"):
        if not f.name.endswith(".smali"):
            continue
        # Quick check for oneseeker in file
        try:
            text = f.read_text("utf-8", errors="replace")
        except:
            continue
        
        if "oneseeker.top" not in text:
            continue
        
        r = str(f.relative_to(APK))
        print(f"=== Found oneseeker in {r} ===")
        lines = text.splitlines(keepends=True)
        
        # Find the method containing oneseeker (method definition comes BEFORE the URL)
        url_line = None

        for i, ln in enumerate(lines):
            if "oneseeker.top" in ln:
                url_line = i
                break

        if url_line is None:
            continue

        # Walk BACKWARDS from URL line to find .method
        method_start = None
        method_name = None
        for i in range(url_line, -1, -1):
            s = lines[i].strip()
            if s.startswith(".method "):
                method_start = i
                method_name = s
                break

        if method_start is None:
            print("  Could not find method containing oneseeker, skipping")
            continue
            
        # Find method end
        for i in range(method_start + 1, min(method_start + 200, len(lines))):
            if lines[i].strip().startswith(".end method"):
                method_end = i
                break
        
        print(f"  Method: {method_name}")
        print(f"  Lines {method_start+1}-{method_end+1}")
        
        # Show the method
        for i in range(method_start, min(method_end or (method_start + 50), len(lines))):
            strip = lines[i].rstrip()
            if i == url_line:
                print(f"  [{i+1}] (URL) {strip[:150]}")
            elif any(x in strip for x in ["invoke", "new-instance", "HttpURL", "connect"]):
                print(f"  [{i+1}] (NET) {strip[:150]}")
            elif i < method_start + 5 or i == method_end:
                print(f"  [{i+1}] {strip[:150]}")
        
        # NOP the method: replace body with return-void
        if method_end:
            indent = " " * 4
            # Keep .method signature and .locals, replace rest
            new_lines = lines[:method_start + 1]
            # Calculate .locals for return-void (needs 0 or 1)
            new_lines.append(f"    .locals 0\n")
            new_lines.append(f"    return-void\n")
            new_lines.append(f".end method\n")
            new_lines.extend(lines[method_end + 1:])
            
            f.write_text("".join(new_lines))
            MODS += 1
            print(f"\n  ✅ NOPped method body → return-void ({len(new_lines)} lines)")
        break
    if MODS > 0:
        break

print(f"\n=== Done: {MODS} files patched ===")
