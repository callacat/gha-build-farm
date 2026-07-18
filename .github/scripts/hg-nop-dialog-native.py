#!/usr/bin/env python3
"""NOP 鹿属 dialog entry — find the class that calls SafeLoader.registerNativesForClass
with class_id=3, then NOP its native method that takes Activity param.

SafeLoader.registerNativesForClass must NOT be touched — it must stay native.

In smali, registerNativesForClass(3, C4409.class) looks like:
  const/4 v0, 0x3
  const-class v1, Lorg/checkerframework/.../X;
  invoke-static {v0, v1}, Lsgcore0/SafeLoader;->registerNativesForClass(ILjava/lang/Class;)V
"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0

print("=== Find C4409 (invokes safeLoader with const/4 0x3) and NOP dialog entry ===")

for f in sorted(APK.rglob("*.smali")):
    if "sgcore0" in str(f) or "SafeLoader" in str(f):
        continue
    text = f.read_text("utf-8", errors="replace")
    # Must call SafeLoader.registerNativesForClass
    if "SafeLoader;->registerNativesForClass" not in text:
        continue
    # Must have const/4 ?v, 0x3 (class_id = 3 = C4409)
    if not re.search(r'const/4\s+[vp]\d+,\s*0x3', text):
        continue

    print(f"  Found C4409 candidate: {f.relative_to(APK)}")
    lines = text.splitlines(keepends=True)
    new_lines = []
    i = 0
    patched = False

    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith(".method ") and "native" in stripped and "Landroid/app/Activity;" in stripped:
            # Dialog entry method — NOP it
            m = re.search(r"\.method\s+(?:\w+\s+)*native\s+(\S+)", stripped)
            method_name = m.group(1) if m else "unknown"
            indent = re.match(r"^(\s*)", stripped).group(1)
            j = i + 1
            depth = 0
            while j < len(lines):
                s2 = lines[j].strip()
                if s2.startswith(".method "): depth += 1
                elif s2.startswith(".end method"):
                    if depth == 0:
                        new_lines.append(f"{indent}.method public static {method_name}(Landroid/app/Activity;)V\n")
                        new_lines.append(f"{indent}    .locals 0\n")
                        new_lines.append(f"{indent}    return-void\n")
                        new_lines.append(f"{indent}.end method\n")
                        i = j + 1
                        patched = True
                        MODS += 1
                        print(f"    ✅ NOP'd: {method_name}")
                        break
                    depth -= 1
                j += 1
            if not patched:
                new_lines.append(lines[i]); i += 1
        else:
            new_lines.append(lines[i]); i += 1

    if patched:
        f.write_text("".join(new_lines), encoding="utf-8")
        break

if MODS == 0:
    print("  ⚠️  C4409 not found (SafeLoader call with class_id=3 not present)")
print(f"\n=== 完成: {MODS} files patched ===")
