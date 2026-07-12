#!/usr/bin/env python3
"""找到破解者植入的更新弹窗 — 精确找法"""
import re, sys
from pathlib import Path

JADX = Path("/tmp/jadx_out/")
APKTOOL = Path("/tmp/apktool_out/")
OUT = "/tmp/trigger-analysis.txt"
out_lines = []
def o(s): out_lines.append(str(s)); print(s)

# 1. Find any smali with ACTION_VIEW + update/download
o("=== ACTION_VIEW + update/download ===")
for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APKTOOL))
        if "androidx" in r: continue
        t = f.read_text("utf-8", errors="replace")
        if "ACTION_VIEW" in t and ("update" in t.lower() or "download" in t.lower()):
            o(f"  {r}")

# 2. Find suspicious external URLs
o("\n=== SUSPICIOUS URLs ===")
for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        t = f.read_text("utf-8", errors="replace")
        urls = re.findall(r'https?://[a-zA-Z0-9./_-]+', t)
        for u in urls:
            if any(x in u for x in ['baidu.com','yuanfudao']):
                r = str(f.relative_to(APKTOOL))
                if 'androidx' not in r and 'android/support' not in r:
                    o(f"  URL={u}  IN={r}")

# 3. Application class behavior
o("\n=== Application class ===")
mf = APKTOOL / "AndroidManifest.xml"
if mf.is_file():
    t = mf.read_text("utf-8", errors="replace")
    app = re.search(r'android:name="([^"]*)"', t[t.find("<application"):t.find(">")])
    if app:
        ac = app.group(1)
        o(f"  Application: {ac}")
        fname = ac.split(".")[-1]
        for sd in sorted(APKTOOL.glob("smali*")):
            for f in sd.rglob(f"{fname}.smali"):
                ct = f.read_text("utf-8", errors="replace")
                for i, l in enumerate(ct.splitlines()):
                    ls = l.strip()
                    if any(k in ls.lower() for k in ['update','dialog','start','url','version','check','intent','activity']):
                        if not ls.startswith('.') and ls:
                            o(f"  {f.relative_to(APKTOOL)}:L{i+1} {ls[:100]}")

# 4. Find noHistory/excludeFromRecents activities (modder tricks)
o("\n=== Hidden activities ===")
if mf.is_file():
    t = mf.read_text("utf-8", errors="replace")
    for m in re.finditer(r'<activity[^>]*>', t):
        act = m.group()
        for flag in ['excludeFromRecents','noHistory','taskAffinity','finishOnTaskLaunch']:
            if flag in act:
                name = re.search(r'android:name="([^"]*)"', act)
                o(f"  {name.group(1) if name else '?'}: {flag}")

# 5. Look for Java code that triggers external URLs
o("\n=== Java: External URL triggers ===")
pkg = "com/phoenix"
for f in sorted(JADX.rglob("*.java")):
    r = str(f.relative_to(JADX))
    if pkg not in r: continue
    t = f.read_text("utf-8", errors="replace")
    if "ACTION_VIEW" in t or "Uri.parse" in t:
        o(f"  {r}")
        for i, l in enumerate(t.splitlines()):
            if "ACTION_VIEW" in l or "Uri.parse" in l:
                o(f"    L{i+1}: {l.strip()[:150]}")

# 6. Find any webview/dialog activity in app namespace
o("\n=== Possible update activities from manifest ===")
if mf.is_file():
    t = mf.read_text("utf-8", errors="replace")
    for m in re.finditer(r'name="([^"]*)"', t):
        name = m.group(1)
        if any(k in name.lower() for k in ['splash','update','ad','dialog','pop','notice','upgrade']):
            o(f"  {name}")

Path(OUT).write_text("\n".join(out_lines))
print(f"Saved to {OUT}")
