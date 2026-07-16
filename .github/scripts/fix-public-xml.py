#!/usr/bin/env python3
"""Remove invalid resource types + clear security check strings from arsc."""
import re, shutil, os, struct
from pathlib import Path

APKTOOL_DIR = '/tmp/apktool_out'

# 1. Delete invalid resource directories under res/
for d in Path(APKTOOL_DIR).glob('res/invalid*'):
    if d.is_dir():
        shutil.rmtree(d)
        print(f'Removed directory: {d}')

# 2. Remove invalid-type <public> entries from public.xml
for f in Path(APKTOOL_DIR).glob('res/values*/public.xml'):
    content = f.read_text(encoding='utf-8', errors='replace')
    new = re.sub(r'<public[^>]*type="invalid\d*"[^>]*/>\s*\n?', '', content)
    if len(new) < len(content):
        f.write_text(new, encoding='utf-8')
        print(f'Fixed {f}: removed {len(content)-len(new)} bytes')

# 3. Clear security check strings in resources.arsc
arsc_path = os.path.join(APKTOOL_DIR, 'resources.arsc')
if os.path.exists(arsc_path):
    with open(arsc_path, 'rb') as f:
        data = bytearray(f.read())

    targets = {
        '当前版本不安全': b'\xe5\xbd\x93\xe5\x89\x8d\xe7\x89\x88\xe6\x9c\xac\xe4\xb8\x8d\xe5\xae\x89\xe5\x85\xa8',
        '请到正规应用市场下载': b'\xe8\xaf\xb7\xe5\x88\xb0\xe6\xad\xa3\xe8\xa7\x84\xe5\xba\x94\xe7\x94\xa8\xe5\xb8\x82\xe5\x9c\xba\xe4\xb8\x8b\xe8\xbd\xbd',
    }

    for name, target_bytes in targets.items():
        idx = data.find(target_bytes)
        if idx != -1:
            # Replace with spaces (same length) instead of null — avoids pool issues
            data[idx:idx+len(target_bytes)] = b' ' * len(target_bytes)
            print(f'Cleared string "{name}" ({len(target_bytes)} bytes) at arsc offset 0x{idx:x}')
        else:
            print(f'WARNING: string "{name}" not found in arsc')

    with open(arsc_path, 'wb') as f:
        f.write(data)
    print('resources.arsc updated')
else:
    print('No resources.arsc found')
