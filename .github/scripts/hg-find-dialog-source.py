#!/usr/bin/env python3
"""Find ALL code paths that build AlertDialogs from server data.
Output: class names, line numbers, and surrounding context."""
import re, json
from pathlib import Path

JADX = Path("/tmp/jadx_out/")
APKTOOL = Path("/tmp/apktool_out/")
OUT = "/tmp/dialog-source-analysis.json"

findings = []

# 1. In jadx Java output: search for AlertDialog.Builder usage
print("=== Phase 1: AlertDialog.Builder in Java ===")
for f in sorted(JADX.rglob("*.java")):
    r = str(f.relative_to(JADX))
    if any(x in r for x in ["/androidx/", "/annotation/", "/org/junit/", "/okhttp/", "/retrofit/"]):
        continue
    t = f.read_text("utf-8", errors="replace")
    if "AlertDialog" in t and ("Builder" in t or "show()" in t):
        lines = t.splitlines()
        for i, ln in enumerate(lines):
            if "AlertDialog" in ln:
                ctx_start = max(0, i-2)
                ctx_end = min(len(lines), i+3)
                ctx = "\n".join(lines[ctx_start:ctx_end])
                findings.append({
                    "file": r,
                    "line": i+1,
                    "context": ctx.strip()[:200],
                })
                print(f"  {r}:{i+1}")
                print(f"    {ctx.strip()[:120]}")
                break

# 2. Search smali for AlertDialog show/create patterns
print("\n=== Phase 2: AlertDialog.Builder.show() in smali ===")
for sd in sorted(APKTOOL.glob("smali*")):
    if not sd.is_dir(): continue
    for f in sd.rglob("*.smali"):
        r = str(f.relative_to(APKTOOL))
        if any(x in r for x in ["/androidx/", "/annotation/", "/org/junit/", "/okhttp/"]):
            continue
        t = f.read_text("utf-8", errors="replace")
        if "AlertDialog;->show()V" in t or "AlertDialog;-><init>" in t:
            lines = t.splitlines()
            for i, ln in enumerate(lines):
                if "AlertDialog" in ln:
                    findings.append({
                        "file": r,
                        "line": i+1,
                        "context": ln.strip()[:200],
                        "type": "smali_AlertDialog"
                    })
                    print(f"  {r}:{i+1}")

# 3. Find the specific class that received the server response
print("\n=== Phase 3: Update response receivers ===")
JAVA_FILES = list(JADX.rglob("*.java"))
print(f"Scanning {len(JAVA_FILES)} Java files...")

# Search for common modder patterns
for pattern in ["getString.*update", "onSuccess.*update", "dialogContent", "showUpdate",
                "mUpdateDialog", "showDialog.*update", "updateInfo", "checkVersion",
                "forceUpdate.*dialog", "UpdatePop", "UpgradePopup"]:
    for f in JAVA_FILES:
        t = f.read_text("utf-8", errors="replace")
        if pattern.lower() in t.lower():
            r = str(f.relative_to(JADX))
            for i, ln in enumerate(t.splitlines()):
                if pattern.lower() in ln.lower():
                    findings.append({
                        "file": r,
                        "line": i+1,
                        "context": ln.strip()[:200],
                        "pattern": pattern
                    })
                    print(f"  [{pattern}] {r}:{i+1}")

# Output
Path(OUT).write_text(json.dumps(findings, indent=2, ensure_ascii=False))
print(f"\n=== Total findings: {len(findings)} ===")
