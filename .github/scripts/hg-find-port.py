#!/usr/bin/env python3
"""Find port 10008 and the surrounding method in smali."""
from pathlib import Path

APKTOOL = Path("/tmp/apktool_out/")
TARGET_PORT = "10008"
TARGET_DOMAIN = "oneseeker"

found = []

# Search in ALL files, not just smali  
for f in sorted(APKTOOL.rglob("*")):
    if not f.is_file(): continue
    r = str(f.relative_to(APKTOOL))
    if any(x in r for x in ["/androidx/", "/annotation/"]): continue
    
    try:
        data = f.read_bytes()
    except:
        continue
    
    # Check for port or domain
    if TARGET_PORT.encode() in data or TARGET_DOMAIN.encode() in data:
        # Try to get context
        try:
            text = data.decode("utf-8", errors="replace")
            lines = text.splitlines()
            for i, ln in enumerate(lines):
                if TARGET_PORT in ln or TARGET_DOMAIN in ln:
                    # Also get surrounding method name
                    ctx_start = max(0, i-10)
                    ctx_end = min(len(lines), i+3)
                    
                    # Find method name above this line
                    method_name = ""
                    for j in range(i-1, max(0, i-15), -1):
                        if ".method " in lines[j]:
                            method_name = lines[j].strip()
                            break
                    
                    found.append(f"  [{r}:{i+1}]")
                    if method_name:
                        found.append(f"    Method: {method_name}")
                    found.append(f"    {ln.strip()[:200]}")
                    break
        except:
            found.append(f"  [{r}] (binary match)")

print("=== FIND PORT 10008 / oneseeker ===")
for line in found:
    print(line)
print(f"\nTotal: {len(found)}")

if found:
    Path("/tmp/port-search.txt").write_text("\n".join(found))
