#!/usr/bin/env python3
"""Fix DEX header checksums (SHA1 at offset 12, Adler32 at offset 8) after apktool rebuild.

Tencent Tinker verifies these checksums at runtime. apktool rebuild modifies DEX files
but doesn't update the checksums, causing ClassNotFoundException for MainApplication.
"""
import hashlib
import sys
import struct
import zlib
from pathlib import Path
import zipfile

APK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/fq-unsigned.apk")

def fix_dex_checksums(dex_data: bytes) -> bytes:
    """Update SHA1 (offset 12-32) and Adler32 (offset 8) in DEX header."""
    if len(dex_data) < 32 or dex_data[:3] != b'dex':
        return dex_data

    # Calculate SHA1 of everything after the first 32 bytes (header)
    sha1 = hashlib.sha1(dex_data[32:]).digest()

    # Calculate Adler32 of everything after the first 12 bytes
    adler32 = zlib.adler32(dex_data[12:]) & 0xffffffff

    # Build new header: magic(8) + checksum(4) + signature(20) + file_size(4) + header_size(4) + endian_tag(4)
    # We only modify checksum (offset 8) and signature (offset 12-32)
    new_header = bytearray(dex_data[:32])
    struct.pack_into('<I', new_header, 8, adler32)
    new_header[12:32] = sha1

    return bytes(new_header) + dex_data[32:]


def main():
    if not APK.exists():
        print(f"APK not found: {APK}")
        sys.exit(1)

    print(f"=== Fixing DEX checksums in {APK} ===")

    with zipfile.ZipFile(APK, 'r') as zin:
        dex_files = [info for info in zin.infolist() if info.filename.endswith('.dex')]
        print(f"Found {len(dex_files)} DEX files")

    # Read all files, fix DEX files, write new APK
    with zipfile.ZipFile(APK, 'r') as zin:
        with zipfile.ZipFile(APK.with_suffix('.fixed.apk'), 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename.endswith('.dex'):
                    fixed = fix_dex_checksums(data)
                    if fixed != data:
                        print(f"  Fixed: {info.filename} (Adler32: {zlib.adler32(fixed[12:]) & 0xffffffff:08x})")
                    else:
                        print(f"  Unchanged: {info.filename}")
                    zout.writestr(info, fixed)
                else:
                    zout.writestr(info, data)

    # Replace original with fixed
    APK.with_suffix('.fixed.apk').replace(APK)
    print(f"✅ Updated {APK}")


if __name__ == '__main__':
    main()