#!/usr/bin/env python3
"""红果短剧 去强制更新 — 单遍扫描"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
CHANGES = 0

for sd in sorted(APK.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APK))
        # Skip AndroidX
        if "/androidx/" in r or "/android/support/" in r: continue
        
        t = f.read_text("utf-8", errors="replace")
        o = t
        
        # setCancelable
        if "setCancelable(false)" in t or "setCancelable (false)" in t:
            t = t.replace("setCancelable (false)", "setCancelable(true)")
            t = t.replace("setCancelable(false)", "setCancelable(true)")
        if "setCanceledOnTouchOutside(false)" in t or "setCanceledOnTouchOutside (false)" in t:
            t = t.replace("setCanceledOnTouchOutside (false)", "setCanceledOnTouchOutside(true)")
            t = t.replace("setCanceledOnTouchOutside(false)", "setCanceledOnTouchOutside(true)")
        
        # PopDefiner force_upgrade
        if "PopDefiner" in r and "force_upgrade" in t:
            t = re.sub(r'sget-object\s+v\d+,\s*Lcom/dragon/read/pop/PopDefiner;->force_upgrade_dialog[^;]*;',
                       'const/4 v0, 0x0', t)
        
        # checkUpdate/ForceUpdate → return false
        if ("checkUpdate" in r or "ForceUpdate" in r) and "const/4 v0, 0x1" in t:
            t = t.replace("const/4 v0, 0x1", "const/4 v0, 0x0")
            t = t.replace("const/4 v1, 0x1", "const/4 v0, 0x0")
        
        # PushImpl forceUpdate → comment
        if "PushImpl" in r and "forceUpdate" in t:
            lines = t.splitlines(keepends=True)
            t = ""
            for l in lines:
                if "forceUpdate" in l and not l.strip().startswith("#"):
                    t += f"# {l}"
                else:
                    t += l
        
        if t != o:
            f.write_text(t)
            CHANGES += 1

print(f"\n=== 补丁完成: {CHANGES} 处修改 ===")
