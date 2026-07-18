#!/usr/bin/env python3
"""Patch libseccore.so — NOP socket() PLT -> return -1.
libseccore uses raw socket for DNS. Block socket -> no dialogs."""
import struct, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

def patch_so(so_path):
    global TOTAL
    data = bytearray(so_path.read_bytes())
    e_shoff = struct.unpack_from('<Q', data, 0x28)[0]
    e_shentsize = struct.unpack_from('<H', data, 0x3A)[0]
    e_shnum = struct.unpack_from('<H', data, 0x3C)[0]
    e_shstrndx = struct.unpack_from('<H', data, 0x3E)[0]
    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        sh_name = struct.unpack_from('<I', data[off:off+4])[0]
        sh_type = struct.unpack_from('<I', data[off+4:off+8])[0]
        sh_flags = struct.unpack_from('<Q', data[off+8:off+16])[0]
        sh_addr = struct.unpack_from('<Q', data[off+16:off+24])[0]
        sh_offset = struct.unpack_from('<Q', data[off+24:off+32])[0]
        sh_size = struct.unpack_from('<Q', data[off+32:off+40])[0]
        sections.append(dict(name=sh_name, type=sh_type, flags=sh_flags, addr=sh_addr, offset=sh_offset, size=sh_size))
    sst = data[sections[e_shstrndx]['offset']:sections[e_shstrndx]['offset']+sections[e_shstrndx]['size']]
    for s in sections:
        end = sst.find(b'\x00', s['name'])
        s['label'] = sst[s['name']:end].decode('ascii', errors='replace') if end > 0 else ''
    dynsym = next(s for s in sections if s.get('label') == '.dynsym')
    dynstr = next(s for s in sections if s.get('label') == '.dynstr')
    relaplt = next((s for s in sections if s.get('label') == '.rela.plt'), None)
    plt = next((s for s in sections if s.get('label') == '.plt'), None)
    if not relaplt or not plt:
        print(f"  Missing .rela.plt or .plt"); return
    ds = data[dynsym['offset']:dynsym['offset']+dynsym['size']]
    dstr = data[dynstr['offset']:dynstr['offset']+dynstr['size']]
    # Build symbol map
    sym_map = {}
    for i in range(0, len(ds), 24):
        st_name = struct.unpack_from('<I', ds[i:i+4])[0]
        st_shndx = struct.unpack_from('<H', ds[i+6:i+8])[0]
        if st_shndx == 0 and st_name > 0:
            n = dstr[st_name:dstr.find(b'\x00', st_name)]
            sym_map[n.decode('ascii', errors='replace')] = i // 24
    # Patch functions
    rd = data[relaplt['offset']:relaplt['offset']+relaplt['size']]
    funcs = ['socket']
    for fname in funcs:
        if fname not in sym_map:
            print(f"  {fname} not in {so_path.name}"); continue
        sidx = sym_map[fname]
        for j in range(0, len(rd), 24):
            r_info = struct.unpack_from('<Q', rd[j+8:j+16])[0]
            if (r_info >> 32) == sidx:
                plt_off = plt['offset'] + 32 + (j // 24) * 16
                if plt_off + 16 <= len(data):
                    # AArch64: movn w0,#0 (w0=-1); ret; nop; nop
                    data[plt_off:plt_off+16] = bytes([0x00,0x00,0x80,0x12, 0xc0,0x03,0x5f,0xd6, 0x1f,0x20,0x03,0xd5, 0x1f,0x20,0x03,0xd5])
                    TOTAL += 1
                    print(f"  ✅ {so_path.relative_to(APK)} plt[{j//24}] {fname} -> -1")
                break
    so_file.write_bytes(bytes(data))

print("=== Patch libseccore.so socket() -> -1 ===")
for so_file in sorted(APK.rglob("libseccore.so")):
    patch_so(so_file)
print(f"\nComplete: {TOTAL} files")
