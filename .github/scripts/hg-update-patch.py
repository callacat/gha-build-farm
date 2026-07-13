#!/usr/bin/env python3
"""Only target: LuckyDogLowUpdateDialog.P1() finish + return-void"""
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
            if '.method public P1(Landroid/content/Intent;Landroid/os/Bundle;)V' in ln:
                for j in range(i+1, min(i+5, len(lines))):
                    if '.locals' in lines[j]:
                        indent = re.match(r'^(\s*)', lines[j]).group(1)
                        lines.insert(j+1, indent + 'invoke-virtual {p0}, Lcom/bytedance/ug/sdk/luckydog/window/dialog/LuckyDogLowUpdateDialog;->finish()V\n')
                        lines.insert(j+2, indent + 'return-void\n')
                        d = True; HITS += 1
                        print(f"  {f.relative_to(APK)}:{j+1}")
                        break
                break
        if d:
            f.write_text("".join(lines))
            print(f"Patched: {f.relative_to(APK)}")

print(f"\n=== Done: {HITS} hit(s) ===")
