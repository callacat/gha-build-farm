#!/usr/bin/env python3
"""NOP C4409.m23296 — 鹿属 dialog native entry point.
Search by content, not filename (smali names are unicode-obfuscated)."""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0

print("=== 1. NOP C4409.m23296 (dialog entry point) ===")

for smali_dir in sorted(APK.glob("smali*")):
    if not smali_dir.is_dir():
        continue
    pkg = smali_dir / "org" / "checkerframework" / "checker" / "signature" / "query" / "security"
    if not pkg.is_dir():
        print(f"  (no checkerframework package in {smali_dir.name})")
        continue

    for smali_file in sorted(pkg.iterdir()):
        if smali_file.suffix != ".smali":
            continue
        text = smali_file.read_text("utf-8", errors="replace")
        if "registerNativesForClass(3," not in text:
            continue  # skip non-C4409 files

        print(f"  Found C4409: {smali_file.relative_to(APK)}")

        # Check if m23296 exists and is native
        if ".method public static native m23296" not in text:
            print(f"  ⚠️  m23296 not found or already patched")
            break

        lines = text.splitlines(keepends=True)
        new_lines = []
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            if s.startswith(".method ") and "m23296" in s and "native" in s:
                # Skip entire method body, replace with return-void
                j = i + 1
                depth = 0
                while j < len(lines):
                    ls = lines[j].strip()
                    if ls.startswith(".method "):
                        depth += 1
                    elif ls.startswith(".end method"):
                        if depth == 0:
                            indent = re.match(r"^(\s*)", lines[i]).group(1)
                            new_lines.append(f"{indent}.method public static m23296(Landroid/app/Activity;)V\n")
                            new_lines.append(f"{indent}    .locals 0\n")
                            new_lines.append(f"{indent}    return-void  # dialog disabled\n")
                            new_lines.append(f"{indent}.end method\n")
                            i = j + 1
                            MODS += 1
                            print(f"  ✅ NOP'd -> return-void")
                            break
                        depth -= 1
                    j += 1
                if j >= len(lines):
                    new_lines.append(lines[i])
                    i += 1
            else:
                new_lines.append(lines[i])
                i += 1

        if MODS > 0:
            smali_file.write_text("".join(new_lines), encoding="utf-8")
        break
    if MODS > 0:
        break

if MODS == 0:
    # Fallback: search ALL smali files for m23296 regardless of path
    print("\n=== Fallback: searching ALL smali for m23296 ===")
    for f in APK.rglob("*.smali"):
        try:
            text = f.read_text("utf-8", errors="replace")
        except:
            continue
        if ".method public static native m23296(Landroid/app/Activity;)V" not in text:
            continue
        # Found it
        lines = text.splitlines(keepends=True)
        new_lines = []
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            if s.startswith(".method ") and "m23296" in s and "native" in s:
                j = i + 1
                depth = 0
                while j < len(lines):
                    ls = lines[j].strip()
                    if ls.startswith(".method "):
                        depth += 1
                    elif ls.startswith(".end method"):
                        if depth == 0:
                            indent = re.match(r"^(\s*)", lines[i]).group(1)
                            new_lines.append(f"{indent}.method public static m23296(Landroid/app/Activity;)V\n")
                            new_lines.append(f"{indent}    .locals 0\n")
                            new_lines.append(f"{indent}    return-void\n")
                            new_lines.append(f"{indent}.end method\n")
                            i = j + 1
                            MODS += 1
                            print(f"  ✅ Found and NOP'd: {f.relative_to(APK)}")
                            break
                        depth -= 1
                    j += 1
                if j >= len(lines):
                    new_lines.append(lines[i])
                    i += 1
            else:
                new_lines.append(lines[i])
                i += 1
        if MODS > 0:
            f.write_text("".join(new_lines), encoding="utf-8")
            break

    if MODS == 0:
        print("  ⚠️  C4409.m23296 not found anywhere!")

print(f"\n=== 完成: {MODS} files patched ===")
