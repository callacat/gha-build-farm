#!/usr/bin/env python3
"""NOP native methods that trigger the 鹿属 dialog — keep class files (no crash)"""
import re, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")

# Target: C4409.smali — entry point that triggers the group dialog
# Change the native m23296() method to return-void
# The class stays intact → SafeLoader.registerNativesForClass succeeds → no crash
TARGET_METHODS = {
    "C4409": {
        "native_method": "m23296",
        "native_sig": r"\.method public static native m23296\(Landroid/app/Activity;\)V",
        "replacement": ".method public static m23296(Landroid/app/Activity;)V\n    .locals 0\n    return-void\n.end method",
    },
    # DialogFragmentC4433 — the dialog itself, make onCreateView create empty view
    # Actually just block the entry point C4409.m23296, the dialog won't trigger
}

MODS = 0

print("=== 1. NOP C4409.m23296 (dialog entry point) ===")
for smali_dir in sorted(APK.glob("smali*")):
    if not smali_dir.is_dir():
        continue
    target = smali_dir / "org" / "checkerframework" / "checker" / "signature" / "query" / "security" / "C4409.smali"
    if target.exists():
        text = target.read_text("utf-8", errors="replace")
        sig = TARGET_METHODS["C4409"]["native_sig"]
        if sig in text:
            # Replace the native method with simple return-void
            # Need to find the .method ... .end method block
            lines = text.splitlines(keepends=True)
            new_lines = []
            i = 0
            in_method = False
            skipped = False
            while i < len(lines):
                stripped = lines[i].strip()
                if stripped.startswith(".method ") and "m23296" in stripped and "native" in stripped:
                    # Skip until .end method
                    in_method = True
                    skipped = True
                    # Find the .end method
                    j = i + 1
                    depth = 0
                    while j < len(lines):
                        s = lines[j].strip()
                        if s.startswith(".method "):
                            depth += 1
                        elif s.startswith(".end method"):
                            if depth == 0:
                                # Replace with simple return-void
                                indent = re.match(r"^(\s*)", lines[i]).group(1)
                                new_lines.append(f"{indent}.method public static m23296(Landroid/app/Activity;)V\n")
                                new_lines.append(f"{indent}    .locals 0\n")
                                new_lines.append(f"{indent}    return-void  # dialog disabled\n")
                                new_lines.append(f"{indent}.end method\n")
                                i = j + 1
                                break
                            depth -= 1
                        j += 1
                    if j >= len(lines):
                        new_lines.append(lines[i])
                        i += 1
                else:
                    new_lines.append(lines[i])
                    i += 1

            target.write_text("".join(new_lines), encoding="utf-8")
            MODS += 1
            print(f"  ✅ {target.relative_to(APK)} — m23296 NOP'd (return-void)")
            break

if MODS == 0:
    print("  ⚠️  C4409.smali not found!")

# 2. Also find ALL smali files calling registerNativesForClass for the dialog classes
# and remove those calls from <clinit> — sanity measure but should not be needed
print("\n=== 2. 清理 <clinit> 中的 registerNativesForClass（可选冗余）===")
removed = 0
for smali_dir in sorted(APK.glob("smali*")):
    if not smali_dir.is_dir():
        continue
    pkg_dir = smali_dir / "org" / "checkerframework" / "checker" / "signature" / "query" / "security"
    if not pkg_dir.is_dir():
        continue
    for smali_file in sorted(pkg_dir.rglob("*.smali")):
        text = smali_file.read_text("utf-8", errors="replace")
        if "registerNativesForClass" not in text:
            continue
        # We KEEP these — they're needed for SafeLoader to work correctly
        # Only NOP the entry point method above
        pass

# 3. Remove redundant NOP-modder step for oneseeker — already exists
print(f"\n=== 完成: {MODS} files patched ===")
