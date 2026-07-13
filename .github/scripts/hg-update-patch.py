#!/usr/bin/env python3
"""Only: LuckyDogLowUpdateDialog.P1() finish+return-void"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
HITS = 0

for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        if f.name != "LuckyDogLowUpdateDialog.smali": continue
        t = f.read_text("utf-8", errors="replace")
        lines = t.splitlines(keepends=True)
        d = False
        for i, ln in enumerate(lines):
            # Try T1 (onCreate proxy via Lancet)
            if '.method public static T1(Lcom/bytedance/ug/sdk/luckydog/window/dialog/LuckyDogLowUpdateDialog;Landroid/content/Intent;Landroid/os/Bundle;)V' in ln:
                indent = re.match(r'^(\s*)', ln).group(1)
                lines.insert(i+1, indent + 'return-void\n')
                d = True; HITS += 1
                print(f"  T1: return-void")
                break
            # Try P1 (actual init)
            if '.method public P1(Landroid/content/Intent;Landroid/os/Bundle;)V' in ln:
                indent = re.match(r'^(\s*)', ln).group(1)
                lines.insert(i+1, indent + 'return-void\n')
                d = True; HITS += 1
                print(f"  P1: return-void")
                break
        if d:
            f.write_text("".join(lines)); HITS += 1

print(f"\n=== Done: {HITS} hit(s) ===")

