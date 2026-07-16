#!/usr/bin/env python3
"""Remove invalid resource types (e.g. invalid15) from public.xml and res/."""
import re, glob, shutil, os
from pathlib import Path

# 1. Delete invalid resource directories under res/
for d in Path('/tmp/apktool_out/res').glob('invalid*'):
    if d.is_dir():
        shutil.rmtree(d)
        print(f'Removed directory: {d}')

# 2. Remove invalid-type <public> entries from public.xml
for f in glob.glob('/tmp/apktool_out/res/values*/public.xml'):
    with open(f) as fh:
        content = fh.read()
    new = re.sub(r'<public[^>]*type="invalid\d*"[^>]*/>\s*\n?', '', content)
    if len(new) < len(content):
        with open(f, 'w') as fh:
            fh.write(new)
        print(f'Fixed {f}: removed {len(content)-len(new)} bytes')
