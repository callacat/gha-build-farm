#!/usr/bin/env python3
"""Hongguo v14 — Find and patch forced-update AlertDialog by resource ID lookup.

Strategy:
  1. Extract R.string IDs for '立即更新' / '温馨提示' from APK via aapt2
  2. Search smali for const instructions referencing those IDs
  3. Find the method that builds an AlertDialog$Builder with those strings
  4. NOP the show() call — dialog never appears on screen

Usage:
  python3 hg-update-patch.py /tmp/apktool_out [/tmp/hg.apk]
  If no APK path given, assume IDs are known and skip step 1.
"""
import re, subprocess, sys
from pathlib import Path

SMALI = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
APK = Path(sys.argv[2]) if len(sys.argv) > 2 else None

TARGET_STRINGS = ["温馨提示", "立即更新", "2026.7.11", "7.2.8.32"]
# ── step 1: extract resource IDs from APK ──────────────────────────

def extract_resource_ids(apk: Path) -> dict[str, str]:
    """Return {hex_resource_id: string_name} for string-type resources."""
    ids: dict[str, str] = {}
    try:
        r = subprocess.run(
            ["aapt2", "dump", "resources", str(apk)],
            capture_output=True, text=True, timeout=60,
        )
        for line in r.stdout.splitlines():
            # aapt2 format:  res 0x7f130000 com.foo:string/bar
            # or with config: spec 0x7f130000 com.foo:string/bar (config mcc...)
            m = re.search(r'(?:res|spec)\s+(0x[0-9a-f]+)\s+\S+:string/(\S+)', line)
            if m:
                ids[m.group(2)] = m.group(1)  # name -> hex_id
    except Exception as exc:
        print(f"  [WARN] aapt2 failed: {exc}", file=sys.stderr)
    return ids

if APK and APK.exists():
    rid_map = extract_resource_ids(APK)
    if rid_map:
        print(f"\n=== Resource IDs found: {len(rid_map)} ===")
    else:
        print("\n  [WARN] no resource IDs from aapt2; searching smali blindly")
else:
    rid_map = {}
    print("\n  [INFO] no APK arg; smali-only search mode")

# Build a set of hex R.string IDs to search for in smali
target_ids: set[str] = set()
if rid_map:
    for name, hex_id in rid_map.items():
        if any(t in name for t in ["update", "update", "upgrade", "upgrade",
                                    "force", "new_version", "tip", "notice",
                                    "confirm", "positive"]):
            target_ids.add(hex_id)
    # Also try to find by reverse lookup from text
    # aapt2 doesn't give us the text value directly — use strings command
    try:
        r2 = subprocess.run(
            ["strings", str(APK)],
            capture_output=True, text=True, timeout=120,
        )
        for line in r2.stdout.splitlines():
            for t in TARGET_STRINGS:
                if t in line:
                    # Found a string — try to find its resource ID by name match
                    for name, hex_id in rid_map.items():
                        if t.lower() in name.lower():
                            target_ids.add(hex_id)
                            print(f"  [MATCH] '{t}' -> R.string.{name} = {hex_id}")
    except Exception:
        pass

    print(f"\n  Target IDs: {', '.join(target_ids) if target_ids else '(none — will scan AlertDialog pattern)'}")

# ── step 2: search smali for the resource IDs ──────────────────────
# Also search for AlertDialog$Builder pattern independently

ALERT_BUILDER_PAT = re.compile(
    r'invoke-virtual\s*\{[^}]*\},\s*Landroid/app/AlertDialog\$Builder;->show\(\)Landroid/app/AlertDialog;'
)
SET_CANCELABLE_FALSE = re.compile(
    r'const/4\s+[vp]\d+,\s*0x0\s*\n'
    r'.*?invoke-virtual\s*\{[^}]*\},\s*Landroid/app/AlertDialog\$Builder;->setCancelable\(Z\)Landroid/app/AlertDialog\$Builder;',
    re.DOTALL,
)

def find_dialog_methods(smali: Path):
    """Yield (file, method_line, method_name, lines) for methods that contain
    AlertDialog$Builder.show() AND reference target resource IDs or patterns."""
    for f in smali.rglob("*.smali"):
        if "/androidx/" in str(f) or "/annotation/" in str(f):
            continue
        text = f.read_text("utf-8", errors="replace")
        lines = text.splitlines(keepends=True)

        # Find method boundaries
        method_starts = [i for i, ln in enumerate(lines) if ln.startswith(".method ")]
        method_ends = [i for i, ln in enumerate(lines) if ln.startswith(".end method")]

        for ms, me in zip(method_starts, method_ends):
            body = "".join(lines[ms:me+1])
            rel = str(f.relative_to(smali))

            # Check for AlertDialog$Builder.show()
            if not ALERT_BUILDER_PAT.search(body):
                continue

            # Check for target resource IDs or setCancelable(false) nearby
            has_target_id = False
            if target_ids:
                for tid in target_ids:
                    pat = tid[2:].lower()  # strip "0x"
                    if pat in body.lower():
                        has_target_id = True
                        break
            else:
                # No IDs — use heuristic: setCancelable(false) in same method
                for i in range(ms, me+1):
                    ln = lines[i]
                    if "const/4" in ln and ", 0x0" in ln:
                        for j in range(i, min(i+5, me+1)):
                            if "setCancelable" in lines[j]:
                                has_target_id = True
                                break
                        if has_target_id:
                            break

            if not has_target_id:
                # Also check if the method has setTitle+setMessage+setPositiveButton triple
                triple = ("setTitle" in body and "setMessage" in body
                          and "setPositiveButton" in body)
                if not triple:
                    continue

            # Found it!
            yield rel, ms, lines[ms].strip(), body, lines

print("\n=== Searching for AlertDialog with target strings ===")
candidates = list(find_dialog_methods(SMALI))

if not candidates:
    print("  No candidates found via AlertDialog$Builder.search — expanding to all show()")
    # Broader search: find any .show() on a Dialog or AlertDialog in any method
    BROAD_BUILDER = re.compile(r'invoke-virtual\s*\{[^}]*\},\s*Landroid/app/AlertDialog(\$Builder)?;->show\(\)')
    for f in SMALI.rglob("*.smali"):
        if "/androidx/" in str(f) or "/annotation/" in str(f):
            continue
        text = f.read_text("utf-8", errors="replace")
        lines = text.splitlines(keepends=True)
        for i, ln in enumerate(lines):
            if BROAD_BUILDER.search(ln):
                # Check backward for setCancelable(false) or setPositiveButton
                method_start = max(0, i - 80)
                context = "".join(lines[method_start:i+1])
                if "setCancelable" in context or "setPositiveButton" in context or "setTitle" in context:
                    rel = str(f.relative_to(SMALI))
                    print(f"  {rel}:{i+1}: {ln.strip()}")
                    print(f"    (first 20 lines back: {''.join(lines[max(0,i-20):i])[:200]})")
                    candidates.append((rel, method_start, "", context, lines))

print(f"\n=== Found {len(candidates)} potential dialog methods ===")

# ── step 3: patch — NOP the show() call ────────────────────────────

PATCHED = 0
for rel, ms, mname, body, lines in candidates:
    # Within this method, find the show() call and nop it
    patched = False
    for i, ln in enumerate(lines):
        if i < ms:
            continue
        m = ALERT_BUILDER_PAT.search(ln)
        if not m:
            continue
        # Replace the show() call with nop
        indent = re.match(r"^(\s*)", ln).group(1)
        lines[i] = f"{indent}# show() was here — patched\n"
        lines[i] = f"{indent}nop\n"
        # Handle move-result-object if present
        if i + 1 < len(lines) and "move-result-object" in lines[i + 1]:
            # Preserve register — point to null
            reg_m = re.search(r'move-result-object\s+(vp?\d+)', lines[i + 1])
            if reg_m:
                reg = reg_m.group(1)
                # Comment out the original move-result
                lines[i + 1] = f"{indent}const/4 {reg}, 0x0  # was move-result-object\n"
            else:
                lines[i + 1] = f"{indent}# move-result was here — patched\n"
        PATCHED += 1
        patched = True
        print(f"  ✅ PATCHED: {rel}:{i+1}")

    if patched:
        f_path = SMALI / rel
        f_path.write_text("".join(lines), encoding="utf-8")

if PATCHED == 0:
    print("  ⚠️  No show() calls patched — falling back to setCancelable sweep")
    # Fallback: find all setCancelable(false) → setCancelable(true)
    for f in SMALI.rglob("*.smali"):
        if "/androidx/" in str(f) or "/annotation/" in str(f):
            continue
        text = f.read_text("utf-8", errors="replace")
        lines = text.splitlines(keepends=True)
        dirty = False
        for i, ln in enumerate(lines):
            # Pattern: const/4 vN, 0x0 followed by invoke-virtual ... setCancelable
            if "const/4" in ln and ", 0x0" in ln:
                reg = re.search(r'const/4\s+(vp?\d+)', ln)
                if not reg:
                    continue
                r = re.escape(reg.group(1))
                set_cancel_line = None
                for j in range(i+1, min(i+4, len(lines))):
                    if re.search(rf'invoke-virtual\s*\{{{r}[^}}]*\}},\s*Landroid/app/Dialog;->setCancelable', lines[j]):
                        set_cancel_line = j
                        break
                if set_cancel_line:
                    indent = re.match(r"^(\s*)", ln).group(1)
                    lines[i] = f"{indent}const/4 {reg.group(1)}, 0x1  # was false → true\n"
                    dirty = True
                    PATCHED += 1
                    print(f"  ✅ FALLBACK PATCHED: {str(f.relative_to(SMALI))}:{i+1} setCancelable(true)")

        if dirty:
            f.write_text("".join(lines), encoding="utf-8")

print(f"\n=== Patch complete: {PATCHED} modifications ===")
