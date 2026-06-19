import zipfile, hashlib

off = zipfile.ZipFile('official.apk')
mod = zipfile.ZipFile('modded.apk')
seen = set()

for f in off.namelist() + mod.namelist():
    if not f.endswith('.dex') or f in seen:
        continue
    seen.add(f)
    od = off.read(f) if f in off.namelist() else None
    md = mod.read(f) if f in mod.namelist() else None
    if od and md:
        if hashlib.sha256(od).hexdigest() != hashlib.sha256(md).hexdigest():
            print(f'DIFF: {f} off={len(od)} mod={len(md)}')
    elif od:
        print(f'OFF-ONLY: {f} ({len(od)})')
    elif md:
        print(f'MOD-ONLY: {f} ({len(md)})')

off.close()
mod.close()
