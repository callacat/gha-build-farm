#!/usr/bin/env python3
"""第一优先:找到含下载URL+弹窗+夸克网盘的类"""
import re, sys
from pathlib import Path

JADX = Path("/tmp/jadx_out/")
APKTOOL = Path("/tmp/apktool_out/")

# Search in Java
print("=== URL references ===")
urls_to_find = ["cashdesk", "download", "quark", "夸克", "立即更新", "立即升级"]
for f in sorted(JADX.rglob("*.java")):
    r = str(f.relative_to(JADX))
    if r.startswith("sources/androidx/") or r.startswith("sources/okio/"): continue
    try:
        t = f.read_text("utf-8", errors="replace")
    except: continue
    for url in urls_to_find:
        if url in t:
            lines = t.splitlines()
            for i, l in enumerate(lines):
                if url in l:
                    print(f"  {r}:L{i+1}")
                    ctx = lines[max(0,i-2):i+1]
                    for ci, cl in enumerate(ctx, max(0,i-2)):
                        print(f"    {cl.strip()[:200]}")
                    print()
            break  # one marker per file

# Search AndroidManifest for update-related activities
print("=== MANIFEST activities ===")
mf = APKTOOL / "AndroidManifest.xml"
if mf.is_file():
    t = mf.read_text("utf-8", errors="replace")
    for m in re.finditer(r'<activity[^>]*name="([^"]*update[^"]*)"[^>]*>', t, re.I):
        print(f"  {m.group(1)}")
    for m in re.finditer(r'<activity[^>]*name="([^"]*Upgrade[^"]*)"[^>]*>', t):
        print(f"  {m.group(1)}")

# Find all Dialog themed activities in manifest
print("\n=== Dialog-themed activities (possible popups) ===")
for m in re.finditer(r'<activity[^>]*theme="[^"]*dialog[^"]*"[^>]*name="([^"]*)"', t, re.I):
    print(f"  {m.group(1)}")

# Find webview activities  
print("\n=== WebView activities ===")
for m in re.finditer(r'<activity[^>]*name="([^"]*WebView[^"]*)"', t):
    print(f"  {m.group(1)}")

# Search for startActivity / openUrl in update context
print("\n=== startActivity with download URL ===")
for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APKTOOL))
        if "androidx/" in r: continue
        t = f.read_text("utf-8", errors="replace")
        if ("download" in t.lower() or "cashdesk" in t) and ("startActivity" in t or "ACTION_VIEW" in t or "openURL" in t):
            print(f"  {r}")
