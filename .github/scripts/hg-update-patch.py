#!/usr/bin/env python3
"""Hongguo v15 — make forced-update dialog dismissable.

Strategy: change every setCancelable(false) to setCancelable(true).
This is a single byte change (0x0 → 0x1) that doesn't alter smali
instruction structure — no VerifyError risk.

The dialog will still appear, but user can tap outside / press back
to dismiss it. Combined with domain poison (oneseeker.top → 127.0.0.1),
the "立即更新" button leads nowhere useful.

Usage: python3 hg-update-patch.py /tmp/apktool_out [/tmp/hg.apk]
"""
import re, sys
from pathlib import Path

SMALI = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")

PATCHED = 0

def is_blacklisted(path: str) -> bool:
    """Skip framework / support / annotation dirs to avoid side effects."""
    return any(x in path for x in ["/androidx/", "/annotation/", "/org/junit/"])

for f in sorted(SMALI.rglob("*.smali")):
    rel = str(f.relative_to(SMALI))
    if is_blacklisted(rel):
        continue

    text = f.read_text("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)
    dirty = False

    for i, ln in enumerate(lines):
        # Pattern: const/4 vN, 0x0 followed closely by ...->setCancelable(Z)...
        if "const/4" not in ln or ", 0x0" not in ln:
            continue
        reg = re.search(r'const/4\s+(vp?\d+),\s*0x0', ln)
        if not reg:
            continue
        r = re.escape(reg.group(1))

        # Look ahead for any setCancelable variant:
        #   Dialog;->setCancelable(Z)V
        #   AlertDialog;->setCancelable(Z)V
        #   AlertDialog$Builder;->setCancelable(Z)Landroid/app/AlertDialog$Builder;
        for j in range(i+1, min(i+6, len(lines))):
            if re.search(rf'invoke-virtual\s*\{{{r}[^}}]*\}},\s*Landroid/app/(Dialog|AlertDialog|\$Builder)->setCancelable\(Z\)', lines[j]):
                indent = re.match(r"^(\s*)", ln).group(1)
                v = reg.group(1)
                lines[i] = f"{indent}const/4 {v}, 0x1  # was false → true (patch v16)\n"
                dirty = True
                PATCHED += 1
                print(f"  ✅ {rel}:{i+1}  -> setCancelable(true)  ({lines[j].strip()[:60]})")
                break
            # Also match setCanceledOnTouchOutside
            if re.search(rf'invoke-virtual\s*\{{{r}[^}}]*\}},\s*Landroid/app/(Dialog|AlertDialog)->setCanceledOnTouchOutside\(Z\)', lines[j]):
                indent = re.match(r"^(\s*)", ln).group(1)
                v = reg.group(1)
                lines[i] = f"{indent}const/4 {v}, 0x1  # was false → true (patch v16 touch)\n"
                dirty = True
                PATCHED += 1
                print(f"  ✅ {rel}:{i+1}  -> setCanceledOnTouchOutside(true)  ({lines[j].strip()[:60]})")
                break

    if dirty:
        f.write_text("".join(lines), encoding="utf-8")

print(f"\n=== Patch complete: {PATCHED} modifications ===")
print("  (setCancelable(false) → true — dialog becomes dismissable)")
print("  No smali instruction structure was changed — no VerifyError risk")
