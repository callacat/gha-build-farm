#!/usr/bin/env python3
"""NOP the 鹿属 dialog entry by finding the native method that takes Activity param
in the C4409 class (identified by registerNativesForClass(3, ...)).

DO NOT touch SafeLoader.registerNativesForClass — it must remain native.
Only NOP the dialog trigger method (the one with Activity parameter)."""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0

print("=== Find C4409 (registerNativesForClass class 3) and NOP dialog entry ===")

for f in sorted(APK.rglob("*.smali")):
    text = f.read_text("utf-8", errors="replace")
    if "registerNativesForClass(3," not in text:
        continue
    # Skip SafeLoader — don't touch it
    if "SafeLoader" in str(f):
        continue

    print(f"  Found C4409: {f.relative_to(APK)}")

    lines = text.splitlines(keepends=True)
    new_lines = []
    i = 0
    patched = False

    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith(".method ") and "native" in stripped and "Landroid/app/Activity;" in stripped:
            # This is the dialog trigger method — NOP it
            # Extract method name
            m = re.search(r"\.method\s+(?:\w+\s+)*native\s+(\S+)", stripped)
            method_name = m.group(1) if m else "unknown"

            indent = re.match(r"^(\s*)", stripped).group(1)
            # Find .end method
            j = i + 1
            depth = 0
            while j < len(lines):
                s2 = lines[j].strip()
                if s2.startswith(".method "):
                    depth += 1
                elif s2.startswith(".end method"):
                    if depth == 0:
                        # Replace with non-native return-void (keep same method name for compatibility)
                        new_lines.append(f"{indent}.method public static {method_name}(Landroid/app/Activity;)V\n")
                        new_lines.append(f"{indent}    .locals 0\n")
                        new_lines.append(f"{indent}    return-void  # dialog entry disabled\n")
                        new_lines.append(f"{indent}.end method\n")
                        i = j + 1
                        patched = True
                        MODS += 1
                        print(f"    ✅ NOP'd: {method_name}")
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
        f.write_text("".join(new_lines), encoding="utf-8")
        break

if MODS == 0:
    print("  ⚠️  C4409 not found or native method with Activity param not present")

# Also check for any other file in the same package calling registerNativesForClass(3
# that might not be C4409
print(f"\n=== 完成: {MODS} files patched ===")
