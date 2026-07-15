#!/usr/bin/env python3
"""Hongguo v21 — NOP the modder's network check instead of poisoning the domain.

The domain oneseeker.top is stored in MainFragmentActivity.smali.
Poisoning to 127.0.0.1 causes TCP RST → app detects "server error" → blocks startup.
Poisoning to 0.0.0.0 causes timeout → same blocking behavior.
NOPing the connection method avoids the network call entirely → no hang + no dialog.
"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0

# Target: MainFragmentActivity.smali
# The oneseeker URL is at line 56416. Find the method around it.
# Since oneseeker is passed to a function that makes network calls,
# we need to find the line and NOP backward to the method start.
TARGET = "remote.oneseeker.top"

for target_file in [
    APK / "smali_classes30/com/dragon/read/pages/main/MainFragmentActivity.smali",
]:
    if not target_file.exists():
        print(f"[SKIP] {target_file} not found")
        continue

    text = target_file.read_text("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)

    # Find oneseeker reference and the method containing it
    oneseeker_line = None
    method_start = None
    method_end = None
    method_name = None

    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if ".method " in stripped:
            method_start = i
            method_name = stripped
        if ".end method" in stripped:
            method_end = i
        if TARGET in ln:
            oneseeker_line = i
            break

    if oneseeker_line is None:
        print(f"[SKIP] {TARGET} not found in {target_file.name}")
        continue

    # Found it! Output the method context for diagnosis
    print(f"=== Found '{TARGET}' in {target_file.name}:{oneseeker_line+1} ===")
    print(f"Method: {method_name}")
    print(f"Method span: lines {method_start+1}-{(method_end or len(lines))}")

    # Show 5 lines around the target for context
    start_ctx = max(0, oneseeker_line - 2)
    end_ctx = min(len(lines), oneseeker_line + 3)
    print("\nContext:")
    for j in range(start_ctx, end_ctx):
        marker = ">>>" if j == oneseeker_line else "   "
        print(f"  {marker} {j+1}: {lines[j].rstrip()[:150]}")

    # Now find the method that MAKES the network call (invoke-* after the const-string)
    # Look for invoke-virtual/static that uses the register containing oneseeker URL
    target_contents = []
    if method_start is not None:
        for j in range(method_start, min(method_start + 100, len(lines))):
            stripped = lines[j].strip()
            # Include method content
            target_contents.append(f"{j+1}: {lines[j].rstrip()[:150]}")
            if ".end method" in stripped:
                break

    target_file_out = Path("/tmp/mainfragment_context.txt")
    target_file_out.write_text("\n".join(target_contents))
    print(f"\nFull method context saved to {target_file_out}")
    MODS += 1

print(f"\n=== Done: {MODS} files analyzed ===")
