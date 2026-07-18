#!/usr/bin/env python3
"""NOP the dialog trigger by finding SafeLoader.registerNativesForClass calls
and removing the invocation + native method bodies for C4409 entry point.
Smali names are obfuscated, so we identify by registerNativesForClass(3,
and also by the signature that takes Activity as parameter."""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0

print("=== 1. Find & NOP C4409 (registerNativesForClass class 3) ===")

for f in sorted(APK.rglob("*.smali")):
    text = f.read_text("utf-8", errors="replace")
    if "registerNativesForClass(3," not in text:
        continue

    print(f"  Found C4409: {f.relative_to(APK)}")
    lines = text.splitlines(keepends=True)
    new_lines = []
    i = 0
    native_found = False

    while i < len(lines):
        stripped = lines[i].strip()
        # Look for any .method with 'native' that takes a single Activity param
        if stripped.startswith(".method ") and "native" in stripped and "Landroid/app/Activity;" in stripped:
            # This is the dialog entry — NOP the entire method
            indent = re.match(r"^(\s*)", stripped).group(1)
            # Extract method name
            m = re.search(r"\.method\s+(?:\w+\s+)*native\s+(\S+)", stripped)
            method_name = m.group(1) if m else "unknown"

            # Find .end method
            j = i + 1
            depth = 0
            while j < len(lines):
                s2 = lines[j].strip()
                if s2.startswith(".method "):
                    depth += 1
                elif s2.startswith(".end method"):
                    if depth == 0:
                        new_lines.append(f"{indent}.method public static {method_name}(Landroid/app/Activity;)V\n")
                        new_lines.append(f"{indent}    .locals 0\n")
                        new_lines.append(f"{indent}    return-void  # dialog blocked\n")
                        new_lines.append(f"{indent}.end method\n")
                        i = j + 1
                        native_found = True
                        MODS += 1
                        print(f"    ✅ NOP'd method: {method_name}")
                        break
                    depth -= 1
                j += 1
            if not native_found:
                new_lines.append(lines[i])
                i += 1
        else:
            new_lines.append(lines[i])
            i += 1

    if native_found:
        f.write_text("".join(new_lines), encoding="utf-8")
        break

# === Also NOP SafeLoader.registerNativesForClass itself ===
# If we can't kill the entry, kill the registration
print("\n=== 2. NOP SafeLoader.registerNativesForClass ===")
for f in sorted(APK.rglob("*.smali")):
    if "SafeLoader" not in f.name:
        continue
    text = f.read_text("utf-8", errors="replace")
    if "registerNativesForClass" not in text:
        continue
    print(f"  Found SafeLoader: {f.relative_to(APK)}")
    lines = text.splitlines(keepends=True)
    new_lines = []
    i = 0
    patched = False
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith(".method ") and "registerNativesForClass" in stripped:
            # NOP the entire method — don't let it register anything
            indent = re.match(r"^(\s*)", stripped).group(1)
            j = i + 1
            depth = 0
            while j < len(lines):
                s2 = lines[j].strip()
                if s2.startswith(".method "):
                    depth += 1
                elif s2.startswith(".end method"):
                    if depth == 0:
                        new_lines.append(f"{indent}.method public static registerNativesForClass(ILjava/lang/Class;)V\n")
                        new_lines.append(f"{indent}    .locals 0\n")
                        new_lines.append(f"{indent}    return-void  # all native registration blocked\n")
                        new_lines.append(f"{indent}.end method\n")
                        i = j + 1
                        patched = True
                        MODS += 1
                        print(f"    ✅ SafeLoader.registerNativesForClass NOP'd")
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
    print("  ⚠️  Nothing found to patch!")

print(f"\n=== 完成: {MODS} files patched ===")
