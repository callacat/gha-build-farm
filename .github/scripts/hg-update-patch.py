#!/usr/bin/env python3
"""Hongguo v17 — NOP AlertDialog$Builder.show() with proper move-result fix.

Strategy: find all AlertDialog$Builder;->show() calls and NOP them.
When a show() call returns an AlertDialog via move-result-object,
replace the move-result with const/4 vN, 0x0 to prevent VerifyError.

Only targets methods in files that also reference the known update URL
(oneseeker.top) to minimize side effects.

Usage: python3 hg-update-patch.py /tmp/apktool_out
"""
import re, sys
from pathlib import Path

SMALI = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
PATCHED = 0

# Regex: AlertDialog$Builder;->show()Landroid/app/AlertDialog;
SHOW_PAT = re.compile(
    r'invoke-virtual\s*\{[^}]*\},\s*Landroid/app/AlertDialog\$Builder;->show\(\)Landroid/app/AlertDialog;'
)
# Regex: Dialog;->show()V
DIALOG_SHOW_PAT = re.compile(
    r'invoke-virtual\s*\{[^}]*\},\s*Landroid/app/Dialog;->show\(\)V'
)

def has_url_ref(text: str) -> bool:
    """Check if file references the update URL (heuristic for relevance)."""
    return any(x in text for x in ["oneseeker", "appUpdate", "force_update", "forceUpgrade"])

def is_blacklisted(path: str) -> bool:
    return any(x in path for x in ["/androidx/", "/annotation/", "/org/junit/"])

def patch_show(lines, i, rel):
    """Patch a show() call at line i: NOP it and fix move-result if present."""
    indent = re.match(r"^(\s*)", lines[i]).group(1)

    # Check next line for move-result-object
    has_move = False
    if i + 1 < len(lines):
        mr = re.search(r'move-result-object\s+(v\d+|p\d+)', lines[i + 1])
        if mr:
            has_move = True
            # Replace move-result with const/4 vN, 0x0
            reg = mr.group(1)
            lines[i + 1] = f"{indent}const/4 {reg}, 0x0  # was move-result-object\n"

    # NOP the show() call
    lines[i] = f"{indent}nop  # show() patched\n"
    return True

# Phase 1: Find + patch in MainFragmentActivity files and any file with update URL
print("=== Phase 1: Patching AlertDialog$Builder.show() ===")
for f in sorted(SMALI.rglob("*.smali")):
    rel = str(f.relative_to(SMALI))
    if is_blacklisted(rel):
        continue

    text = f.read_text("utf-8", errors="replace")
    lines = text.splitlines(keepends=True)

    # Quick pass: does this file have any show() call at all?
    if "->show()" not in text:
        continue

    # Only patch files that either reference the update URL
    # OR are in the main app package (skip system libraries)
    if not has_url_ref(text) and "com/phoenix/read/" not in rel:
        continue

    dirty = False
    for i, ln in enumerate(lines):
        m = SHOW_PAT.search(ln)
        if not m:
            continue
        dirty = patch_show(lines, i, rel) or dirty
        PATCHED += 1
        print(f"  ✅ {rel}:{i+1}  AlertDialog$Builder.show()")

    if dirty:
        f.write_text("".join(lines), encoding="utf-8")

# Phase 2: Fallback — patch any Dialog.show() that's near update URL context
if PATCHED == 0:
    print("\n=== Phase 2: Phase 1 had 0 hits — trying Dialog.show() ===")
    for f in sorted(SMALI.rglob("*.smali")):
        rel = str(f.relative_to(SMALI))
        if is_blacklisted(rel):
            continue
        text = f.read_text("utf-8", errors="replace")
        # Only process files with some update-related keywords
        if not has_url_ref(text) and "com/phoenix/read/" not in rel:
            continue
        if "->show()V" not in text:
            continue

        lines = text.splitlines(keepends=True)
        dirty = False
        for i, ln in enumerate(lines):
            m = DIALOG_SHOW_PAT.search(ln)
            if not m:
                continue
            # Check that this show() is under a method that has setCancelable/setPositiveButton
            # Look backward to find method start
            method_start = i
            for j in range(i, max(i-100, 0), -1):
                if lines[j].startswith(".method "):
                    method_start = j
                    break
            method_body = "".join(lines[method_start:i+1])
            if "setCancelable" not in method_body and "setPositiveButton" not in method_body:
                continue  # Not a dialog show, skip

            indent = re.match(r"^(\s*)", ln).group(1)
            lines[i] = f"{indent}nop  # Dialog.show() patched\n"
            dirty = True
            PATCHED += 1
            print(f"  ✅ {rel}:{i+1}  Dialog.show()")

        if dirty:
            f.write_text("".join(lines), encoding="utf-8")

# Phase 3: Last resort — global Dialog.show() in entire APK
if PATCHED == 0:
    print("\n=== Phase 3: Global Dialog.show() sweep ===")
    for f in sorted(SMALI.rglob("*.smali")):
        rel = str(f.relative_to(SMALI))
        if is_blacklisted(rel):
            continue
        text = f.read_text("utf-8", errors="replace")
        if "->show()V" not in text:
            continue
        lines = text.splitlines(keepends=True)
        dirty = False
        for i, ln in enumerate(lines):
            if DIALOG_SHOW_PAT.search(ln):
                indent = re.match(r"^(\s*)", ln).group(1)
                lines[i] = f"{indent}nop  # show() globally patched\n"
                dirty = True
                PATCHED += 1
                print(f"  ⚠️  {rel}:{i+1}  Dialog.show() (global)")
        if dirty:
            f.write_text("".join(lines), encoding="utf-8")

print(f"\n=== Patch complete: {PATCHED} show() calls NOPped ===")
print("  (No VerifyError: move-result-object replaced with const/4 vN, 0x0)")
