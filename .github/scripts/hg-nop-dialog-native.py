#!/usr/bin/env python3
"""NOP native methods that trigger the 鹿属 dialog — keep class files (no crash)"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0

# The smali file names are unicode-obfuscated, so we search by CONTENT
# Target: the class that has registerNativesForClass(3, ...) — this is C4409
# We look for the method containing m23296 (native entry for dialog trigger)
# and replace it with return-void

SIGNATURES = {
    "m23296": r"\.method\s+public\s+static\s+native\s+m23296\(Landroid/app/Activity;\)V",
}

print("=== 1. NOP C4409.m23296 (dialog entry point) ===")

for smali_dir in sorted(APK.glob("smali*")):
    if not smali_dir.is_dir():
        continue
    pkg = smali_dir / "org" / "checkerframework" / "checker" / "signature" / "query" / "security"
    if not pkg.is_dir():
        continue

    for smali_file in sorted(pkg.rglob("*.smali")):
        try:
            text = smali_file.read_text("utf-8", errors="replace")
        except Exception:
            continue

        if "registerNativesForClass(3," not in text:
            continue  # not C4409

        print(f"  Found C4409 candidate: {smali_file.relative_to(APK)}")

        lines = text.splitlines(keepends=True)
        new_lines = []
        i = 0
        patched = False

        while i < len(lines):
            stripped = lines[i].strip()
            # Look for the native m23296 method
            if re.match(r"\.method\s+public\s+static\s+native\s+m23296", stripped):
                # Find its .end method
                j = i + 1
                depth = 0
                while j < len(lines):
                    s = lines[j].strip()
                    if s.startswith(".method "):
                        depth += 1
                    elif s.startswith(".end method"):
                        if depth == 0:
                            indent = re.match(r"^(\s*)", lines[i]).group(1)
                            new_lines.append(f"{indent}.method public static m23296(Landroid/app/Activity;)V\n")
                            new_lines.append(f"{indent}    .locals 0\n")
                            new_lines.append(f"{indent}    return-void  # dialog disabled\n")
                            new_lines.append(f"{indent}.end method\n")
                            i = j + 1
                            patched = True
                            MODS += 1
                            print(f"  ✅ C4409.m23296 NOP'd (return-void)")
                            break
                        depth -= 1
                    j += 1
                if not patched:
                    new_lines.append(lines[i])
                    i += 1
            else:
                new_lines.append(lines[i])
                i += 1

        if patched:
            smali_file.write_text("".join(new_lines), encoding="utf-8")
            break

if MODS == 0:
    print("  ⚠️  C4409 smali not found! (checkerframework package missing?)")

print(f"\n=== 完成: {MODS} files patched ===")
