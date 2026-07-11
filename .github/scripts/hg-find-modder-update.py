#!/usr/bin/env python3
"""找到破解者植入的更新弹窗代码 — 输出保存到 /tmp/trigger-analysis.txt"""
import re, sys
from pathlib import Path

JADX = Path("/tmp/jadx_out/")
APKTOOL = Path("/tmp/apktool_out/")
OUT = "/tmp/trigger-analysis.txt"
lines = []

def o(s=""):
    lines.append(str(s))
    print(s)

# 1. 搜索所有 Java 文件中的硬编码 URL
o("=== HARDCODED HTTP URLS IN APP PACKAGE (non-ByteDance) ===")
for f in sorted(JADX.rglob("*.java")):
    t = f.read_text("utf-8", errors="replace")
    urls = re.findall(r'https?://[^"\' )]+', t)
    urls = [u for u in urls if not any(x in u for x in ['google','android','w3.org','xmlpull','github','fqnovel','snssdk','bytedance','zijieapi','pstatp','byteimg','schemas','maven','apache','gradle','spring'])]
    if urls:
        r = str(f.relative_to(JADX))[:100]
        o(f"  {r}")
        for u in urls[:5]:
            o(f"    URL: {u}")

# 2. 在 smali 里搜索夸克/下载
o("\n=== KEYWORDS in smali ===")
for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        t = f.read_text("utf-8", errors="replace")
        for kw in ["quark", "夸克", "立即更新", "立即升级", "cashdesk"]:
            if kw in t.lower() or kw in t:
                o(f"  {f.relative_to(APKTOOL)}: '{kw}' found")

# 3. Manifest activities
o("\n=== MANIFEST KEY INFO ===")
mf = APKTOOL / "AndroidManifest.xml"
if mf.is_file():
    t = mf.read_text("utf-8", errors="replace")
    for m in re.finditer(r'android:name="([^"]*)"', t):
        name = m.group(1)
        if any(k in name.lower() for k in ['splash','update','ad','launcher','main']):
            o(f"  {name}")
    app = re.search(r'<application[^>]*android:name="([^"]*)"', t)
    if app: o(f"  Application class: {app.group(1)}")

# 4. Search for startActivity / open browser in app package
o("\n=== startActivity / openURL / browser ===")
for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APKTOOL))
        t = f.read_text("utf-8", errors="replace")
        if ("startActivity" in t or "ACTION_VIEW" in t or "openURL" in t) and ("update" in t.lower() or "url" in t.lower() or "download" in t.lower()):
            o(f"  {r}")

Path(OUT).write_text("\n".join(lines))
print(f"\n=== Analysis saved to {OUT} ===")
