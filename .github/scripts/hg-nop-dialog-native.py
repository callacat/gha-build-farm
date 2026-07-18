#!/usr/bin/env python3
"""NOP 鹿属 dialog entry — find C4409 by SafeLoader call + const/4 0x3.

IMPORTANT: In smali, the method declaration is:
  .method public static native NAME(PARAMS)RETURN
Method name and params are CONCATENATED with no space.
Extract name careful of  unicode chars."""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
MODS = 0

print("=== Find C4409 (SafeLoader call + class_id=3) and NOP dialog entry ===")

for f in sorted(APK.rglob("*.smali")):
    if "SafeLoader" in str(f):
        continue
    text = f.read_text("utf-8", errors="replace")
    if "SafeLoader;->registerNativesForClass" not in text:
        continue
    if not re.search(r'const/4\s+[vp]\d+,\s*0x3', text):
        continue

    print(f"  Found C4409: {f.relative_to(APK)}")
    lines = text.splitlines(keepends=True)
    new_lines = []
    i = 0
    patched = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith(".method ") and "native" in stripped and "Landroid/app/Activity;" in stripped:
            # Keep the original .method line EXACTLY as-is, just remove "native" keyword
            # Smali method names are unicode and CONCATENATED with params (no space)
            new_method_line = line.replace(" native ", " ")  # safe: keep everything else
            indent = re.match(r"^(\s*)", line).group(1)
            j = i + 1
            depth = 0
            while j < len(lines):
                s2 = lines[j].strip()
                if s2.startswith(".method "):
                    depth += 1
                elif s2.startswith(".end method"):
                    if depth == 0:
                        new_lines.append(new_method_line)
                        new_lines.append(f"{indent}    .locals 0\n")
                        new_lines.append(f"{indent}    return-void\n")
                        new_lines.append(lines[j])  # keep original .end method
                        i = j + 1
                        patched = True
                        MODS += 1
                        print(f"    ✅ NOP'd dialog entry method ({line.strip()[:80]})")
                        break
                    depth -= 1
                j += 1
            if not patched:
                new_lines.append(line); i += 1
        else:
            new_lines.append(line); i += 1

    if patched:
        f.write_text("".join(new_lines), encoding="utf-8")
        break

if MODS == 0:
    print("  ⚠️  C4409 not found!")
print(f"\n=== 完成: {MODS} files patched ===")
