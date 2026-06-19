import zipfile, sys

off = zipfile.ZipFile('official.apk')
mod = zipfile.ZipFile('modded.apk')

off_libs = {f: off.getinfo(f).file_size for f in off.namelist()
            if f.startswith('lib/arm64-v8a/') and f.endswith('.so')}
mod_libs = {f: mod.getinfo(f).file_size for f in mod.namelist()
            if f.startswith('lib/arm64-v8a/') and f.endswith('.so')}

common = 0
for f in sorted(set(list(off_libs.keys()) + list(mod_libs.keys()))):
    os = off_libs.get(f, 0)
    ms = mod_libs.get(f, 0)
    if os == 0:
        print(f'MOD-ONLY: {f} size={ms}')
    elif ms == 0:
        print(f'OFF-ONLY: {f} size={os}')
    elif os != ms:
        print(f'SIZE-DIFF: {f} off={os} mod={ms} delta={ms-os}')
    else:
        common += 1

print(f'Common identical: {common} libs match byte-for-byte')
off.close()
mod.close()
