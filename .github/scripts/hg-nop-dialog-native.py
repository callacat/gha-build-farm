#!/usr/bin/env python3
"""Patch libseccore.so — NOP gethostbyname PLT -> return NULL.
All three dialogs load remote content. DNS failure = no dialogs."""
import struct, sys
from pathlib import Path

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/apktool_out")
TOTAL = 0

def patch_so(so_path):
    global TOTAL
    data = bytearray(so_path.read_bytes())
    # Parse ELF
    e_shoff = struct.unpack_from('<Q', data, 0x28)[0]
    e_shentsize = struct.unpack_from('<H', data, 0x3A)[0]
    e_shnum = struct.unpack_from('<H', data, 0x3C)[0]
    e_shstrndx = struct.unpack_from('<H', data, 0x3E)[0]
    # Read sections
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
    # Section names
    sst = data[sections[e_shstrndx]['offset']:sections[e_shstrndx]['offset']+sections[e_shstrndx]['size']]
    for s in sections:
        end = sst.find(b'\x00', s['name'])
        s['label'] = sst[s['name']:end].decode('ascii', errors='replace') if end > 0 else ''
    # Get dynsym/dynstr
    dynsym = next(s for s in sections if s.get('label') == '.dynsym')
    dynstr = next(s for s in sections if s.get('label') == '.dynstr')
    relaplt = next((s for s in sections if s.get('label') == '.rela.plt'), None)
    plt = next((s for s in sections if s.get('label') == '.plt'), None)
    if not relaplt or not plt:
        print(f"  No .rela.plt or .plt"); return
    ds = data[dynsym['offset']:dynsym['offset']+dynsym['size']]
    dstr = data[dynstr['offset']:dynstr['offset']+dynstr['size']]
    # Find gethostbyname index
    host_idx = None
    for i in range(0, len(ds), 24):
        st_name = struct.unpack_from('<I', ds[i:i+4])[0]
        st_shndx = struct.unpack_from('<H', ds[i+6:i+8])[0]
        if st_shndx != 0: continue  # skip defined symbols
        n = dstr[st_name:dstr.find(b'\x00', st_name)]
        if n == b'gethostbyname':host_idx = i // 24; break
    if host_idx is None:
        print(f"  gethostbyname not in {so_path.name}"); return
    # Find rela.plt entry for this symbol
    rd = data[relaplt['offset']:relaplt['offset']+relaplt['size']]
    plt_idx = None
    for i in range(0, len(rd), 24):
        r_info = struct.unpack_from('<Q', rd[i+8:i+16])[0]
        if (r_info >> 32) == host_idx:plt_idx = i // 24; break
    if plt_idx is None:print(f"  gethostbyname rela not found");return
    # AArch64 PLT: PLT[0]=32 bytes, PLT[N]=16 bytes
    plt_off = plt['offset'] + 32 + plt_idx * 16
    # Patch: mov x0,#0; ret; nop; nop
    data[plt_off:plt_off+16] = bytes([0x00,0x00,0x80,0xd2,0xc0,0x03,0x5f,0xd6,0x1f,0x20,0x03,0xd5,0x1f,0x20,0x03,0xd5])
    so_path.write_bytes(bytes(data))
    TOTAL += 1
    print(f"  ✅ {so_path.relative_to(APK)} plt[{plt_idx}] gethostbyname -> NULL")

print("=== Patch libseccore.so gethostbyname -> NULL ===")
for so_file in sorted(APK.rglob("libseccore.so")):
    patch_so(so_file)
print(f"\nComplete: {TOTAL} files")
