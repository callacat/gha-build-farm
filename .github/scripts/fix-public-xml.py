#!/usr/bin/env python3
"""Remove invalid resource types (e.g. invalid15) from public.xml files."""
import re, glob
for f in glob.glob('/tmp/apktool_out/res/values*/public.xml'):
    with open(f) as fh:
        content = fh.read()
    new = re.sub(r'<public[^>]*type="invalid\d*"[^>]*/>\s*\n?', '', content)
    if len(new) < len(content):
        with open(f, 'w') as fh:
            fh.write(new)
        print(f'Fixed {f}: removed {len(content)-len(new)} bytes')
