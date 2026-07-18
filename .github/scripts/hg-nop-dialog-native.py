#!/usr/bin/env python3
"""Block 鹿属 dialog via network config + NOP smali entry points.

Native code (libseccore.so) can call DialogFragment directly via JNI,
bypassing Java smali. Use Android Network Security Config domain
blacklist as the primary defense (system-level, native can't bypass).
Plus NOP C4409 + DialogFragment smali methods as secondary defense."""
import re, sys, shutil
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

# ── Phase 1: Block remote.oneseeker.top via network_security_config ──
print("=== Phase 1: network_security_config domain block ===")
# Find res/xml/e.xml (network security config)
for xml_file in APK.rglob("res/xml/e.xml"):
    text = xml_file.read_text("utf-8", errors="replace")
    if "remote.oneseeker.top" in text:
        print(f"  Already blocked: {xml_file.relative_to(APK)}")
    else:
        # Add domain-config block BEFORE </network-security-config>
        block = """    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="true">remote.oneseeker.top</domain>
        <domain includeSubdomains="true">oneseeker.top</domain>
        <domain includeSubdomains="true">dongle.oneseeker.top</domain>
        <domain includeSubdomains="true">changzhi.top</domain>
    </domain-config>
"""
        text = text.replace("</network-security-config>", block + "</network-security-config>")
        xml_file.write_text(text, encoding="utf-8")
        print(f"  ✅ Added domain block to {xml_file.relative_to(APK)}")
        TOTAL += 1
    break

# ── Phase 2: NOP C4409 (class_id=3) as secondary defense ──
print("\n=== Phase 2: NOP C4409 (class_id=0x3) ===")
for f in sorted(APK.rglob("*.smali")):
    if "SafeLoader" in str(f): continue
    text = f.read_text("utf-8", errors="replace")
    if "SafeLoader;->registerNativesForClass" not in text: continue
    found_id = any(re.search(r'const/4\s+[vp]\d+,\s*0x3', ln) for ln in text.split("\n"))
    if not found_id: continue
    print(f"  Found: {f.relative_to(APK)}")
    lines = text.splitlines(keepends=True)
    new_lines, i, patched = [], 0, False
    while i < len(lines):
        line, stripped = lines[i], lines[i].strip()
        if stripped.startswith(".method ") and "native" in stripped and "Landroid/app/Activity;" in stripped:
            new_line, indent = line.replace(" native ", " "), re.match(r"^(\s*)", line).group(1)
            j, depth = i + 1, 0
            while j < len(lines):
                s2 = lines[j].strip()
                depth += s2.startswith(".method ")
                if s2.startswith(".end method"):
                    if depth == 0:
                        new_lines.append(new_line); new_lines.append(f"{indent}    .locals 0\n")
                        new_lines.append(f"{indent}    return-void\n"); new_lines.append(lines[j])
                        i, patched, TOTAL = j + 1, True, TOTAL + 1; print(f"    ✅ NOP'd")
                        break
                    depth -= 1
                j += 1
            if not patched: new_lines.append(line); i += 1
        else: new_lines.append(line); i += 1
    if patched: f.write_text("".join(new_lines), encoding="utf-8"); break

print(f"\n=== Complete: {TOTAL} modifications ===")
