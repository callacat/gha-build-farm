#!/usr/bin/env python3
"""
hg-smali-stub.py — Smali method body stubbing for ad SDK removal.

Strategy: instead of deleting ad SDK class files (which causes
ClassNotFoundException at runtime), replace method bodies with minimal
return stubs. The class structure stays intact but all methods return
defaults (null/false/0/void) — the SDK initializes without error and
does nothing.

Return type → stub mapping:
  V (void)         → return-void
  Z (boolean)      → const/4 v0, 0x0; return v0
  I/F (int/float)  → const/4 v0, 0x0; return v0
  J/D (long/double)→ const-wide/16 v0, 0x0; return-wide v0
  object           → const/4 v0, 0x0; return-object v0
  String           → const-string v0, ""; return-object v0

Special: ContentProvider.onCreate() → return true (0x1) instead of false.

Usage:
  python3 hg-smali-stub.py --source /tmp/apktool_out --ad-config config.json
"""

from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path


# ── Stub templates ──────────────────────────────────────────────
# Each: (locals_needed, [opcodes])
STUB_TEMPLATES: dict[str, tuple[int, list[str]]] = {
    'V': (0, ['return-void']),
    'Z': (1, ['const/4 v0, 0x0', 'return v0']),
    'B': (1, ['const/4 v0, 0x0', 'return v0']),
    'S': (1, ['const/4 v0, 0x0', 'return v0']),
    'C': (1, ['const/4 v0, 0x0', 'return v0']),
    'I': (1, ['const/4 v0, 0x0', 'return v0']),
    'F': (1, ['const/4 v0, 0x0', 'return v0']),
    'J': (2, ['const-wide/16 v0, 0x0', 'return-wide v0']),
    'D': (2, ['const-wide/16 v0, 0x0', 'return-wide v0']),
}

# ContentProvider.onCreate() must return true
STUB_ONCREATE_TRUE = (1, ['const/4 v0, 0x1', 'return v0'])

# String return: empty string instead of null (safer for callers)
STUB_STRING = (1, ['const-string v0, ""', 'return-object v0'])

OBJECT_STUB = (1, ['const/4 v0, 0x0', 'return-object v0'])


# ── Regex ───────────────────────────────────────────────────────

METHOD_RE = re.compile(r'^(\s*)\.method\b(.*)$')
LOCALS_RE = re.compile(r'^\s*\.(locals|registers)\s+(\d+)\s*$')
END_METHOD_RE = re.compile(r'^\s*\.end\s+method\s*$')
PROVIDER_SUPER_RE = re.compile(r'\.super\s+L[a-zA-Z/]*(?:ContentProvider|InitProvider|PangleProvider|Provider);')


def extract_return_type(method_sig: str) -> str | None:
    """Extract return-type suffix from a smali method signature.

    'onClick(Landroid/view/View;)Z'            → 'Z'
    'toString()Ljava/lang/String;'             → 'Ljava/lang/String;'
    'getData()[B'                               → '[B'
    '<init>(Landroid/content/Context;)V'        → 'V'
    """
    idx = method_sig.rfind(')')
    if idx == -1:
        return None
    return method_sig[idx + 1:]


def is_skip_method(sig_token: str, attrs: list[str]) -> bool:
    """Return True if this method should be left untouched."""
    if 'abstract' in attrs or 'native' in attrs:
        return True
    # <init> / <clinit> — constructors must keep their bodies
    if '<init>' in sig_token or '<clinit>' in sig_token:
        return True
    return False


def is_string_return(ret_type: str) -> bool:
    """True if return type is a CharSequence/String."""
    return ret_type in (
        'Ljava/lang/String;',
        'Ljava/lang/CharSequence;',
        'Ljava/lang/CharSequence;',
    )


def is_provider_class(block_start: list[str], limit: int = 15) -> bool:
    """Quick scan the first N lines of a smali file for ContentProvider superclass."""
    for line in block_start:
        if PROVIDER_SUPER_RE.search(line):
            return True
        # .method means we passed the header — stop searching
        if METHOD_RE.match(line):
            break
    return False


def build_stub(ret_type: str, *, oncreate: bool = False) -> tuple[int, list[str]] | None:
    """Return (locals_needed, [body_opcodes]) for the given return type."""
    if oncreate and ret_type == 'Z':
        return STUB_ONCREATE_TRUE

    if is_string_return(ret_type):
        return STUB_STRING

    first_char = ret_type[0] if ret_type else ''
    if first_char in STUB_TEMPLATES:
        return STUB_TEMPLATES[first_char]

    # All object references (L...;) and arrays ([...) → null
    return OBJECT_STUB


# ── Method block processing ─────────────────────────────────────

def stub_method_block(block: list[str], is_provider: bool) -> list[str] | None:
    """
    Process a single method block (from .method to .end method).
    Return a replacement block, or None to keep the original.
    """
    first = block[0].strip()
    m = METHOD_RE.match(block[0])
    assert m is not None

    indent = m.group(1)
    rest = m.group(2).strip()
    tokens = rest.split()
    sig = tokens[-1]   # e.g. 'onClick(Landroid/view/View;)Z'
    attrs = tokens[:-1]  # e.g. ['public', 'static']

    if is_skip_method(sig, attrs):
        return None

    ret = extract_return_type(sig)
    if ret is None:
        return None

    # Detect ContentProvider.onCreate()
    oncreate = is_provider and 'onCreate' in sig and ret == 'Z'

    stub = build_stub(ret, oncreate=oncreate)
    if stub is None:
        return None

    locals_needed, opcodes = stub

    # ── Build replacement block ──
    out: list[str] = [block[0]]  # Keep .method line

    # Scan for .locals / .registers, update if needed
    found_locals = False
    for line in block[1:-1]:  # Skip .method and .end method
        lm = LOCALS_RE.match(line)
        if lm:
            directive = lm.group(1)  # 'locals' or 'registers'
            current = int(lm.group(2))
            if current < locals_needed:
                out.append(f'{indent}.{directive} {locals_needed}\n')
            else:
                out.append(line)  # Keep original
            found_locals = True
            break

    if not found_locals:
        out.append(f'{indent}.locals {locals_needed}\n')

    # Insert stub body opcodes
    for op in opcodes:
        out.append(f'{indent}    {op}\n')

    # Keep .end method
    out.append(block[-1])

    return out


# ── File-level stubbing ────────────────────────────────────────

def stub_smali_file(filepath: Path) -> tuple[bool, int]:
    """
    Stub all eligible methods in one .smali file.
    Returns (modified_flag, methods_stubbed_count).
    """
    text = filepath.read_text('utf-8', errors='replace')
    lines = text.splitlines(keepends=True)

    is_provider = is_provider_class(lines[:20])
    modified = False
    stubbed = 0
    out: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i]

        if METHOD_RE.match(line):
            # Collect the full method block
            end_idx = i + 1
            while end_idx < len(lines) and not END_METHOD_RE.match(lines[end_idx]):
                end_idx += 1
            if end_idx >= len(lines):
                out.append(line)
                i += 1
                continue

            block = lines[i:end_idx + 1]
            replacement = stub_method_block(block, is_provider)

            if replacement is not None:
                out.extend(replacement)
                modified = True
                stubbed += 1
            else:
                out.extend(block)  # Keep original (constructor/abstract)

            i = end_idx + 1
        else:
            out.append(line)
            i += 1

    if modified:
        filepath.write_text(''.join(out), encoding='utf-8')

    return modified, stubbed


def stub_package(source: Path, pkg_path: str, quiet: bool = False) -> tuple[int, int]:
    """
    Stub all smali files under a package directory across all smali_N dirs.
    Returns (files_stubbed, methods_stubbed).
    """
    total_files = 0
    total_methods = 0

    for smali_dir in sorted(source.glob('smali*')):
        pkg_dir = smali_dir / pkg_path
        if not pkg_dir.is_dir():
            continue

        smali_files = sorted(pkg_dir.rglob('*.smali'))
        if not smali_files:
            continue

        for smali_file in smali_files:
            mod, cnt = stub_smali_file(smali_file)
            if mod:
                total_files += 1
                total_methods += cnt
                if not quiet:
                    rel = smali_file.relative_to(source)
                    print(f'  ✓ {rel}  ({cnt} methods)')

    return total_files, total_methods


# ── Manifest helpers ────────────────────────────────────────────

def remove_providers_from_manifest(source: Path, providers: list[str]) -> int:
    """
    Remove specified <provider> entries from AndroidManifest.xml.
    Returns count of removed entries.
    """
    manifest = source / 'AndroidManifest.xml'
    if not manifest.exists():
        print('  ⚠ AndroidManifest.xml not found')
        return 0

    text = manifest.read_text('utf-8', errors='replace')
    original = text
    count = 0

    for provider_name in providers:
        # Pattern: <provider android:name="com.bytedance.sdk.openadsdk.InitProvider" ... />
        # or multi-line form
        pattern = re.compile(
            r'<provider\s+[^>]*' + re.escape(provider_name) + r'[^>]*/>\s*',
            re.DOTALL
        )
        # Also try: <provider ... android:name="x"\n  ... /> (multi-line close)
        pattern2 = re.compile(
            r'<provider\s+[^>]*' + re.escape(provider_name) + r'[^>]*</provider>\s*',
            re.DOTALL
        )
        text, n1 = pattern.subn('', text)
        text, n2 = pattern2.subn('', text)
        count += n1 + n2

    if count > 0:
        manifest.write_text(text, encoding='utf-8')
    return count


def clean_ad_permissions(source: Path, permissions: list[str]) -> int:
    """Remove specified <uses-permission> lines from AndroidManifest.xml."""
    manifest = source / 'AndroidManifest.xml'
    if not manifest.exists():
        return 0

    text = manifest.read_text('utf-8', errors='replace')
    original = text
    count = 0

    for perm in permissions:
        # Match <uses-permission ... android:name="perm" ... />
        pat = re.compile(
            r'<uses-permission\s+[^>]*' + re.escape(perm) + r'[^>]*/>\s*',
        )
        text, n = pat.subn('', text)
        count += n

    if count > 0:
        manifest.write_text(text, encoding='utf-8')
    return count


# ── Main ────────────────────────────────────────────────────────

def load_config(path: str) -> dict:
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Smali method body stubbing for ad SDK removal',
    )
    parser.add_argument('--source', required=True, help='apktool output directory')
    parser.add_argument('--ad-config', required=True, help='ad-removal.json path')
    parser.add_argument('--quiet', action='store_true', help='less verbose output')
    args = parser.parse_args()

    source = Path(args.source)
    config = load_config(args.ad_config)
    quiet = args.quiet

    # ── Phase 1: Stub methods in target packages ──
    packages = config.get('packages_to_stub', [])
    if packages:
        print(f'\n=== Stubbing {len(packages)} packages ===')
        total_files = 0
        total_methods = 0
        for pkg in packages:
            print(f'\n  📁 {pkg}:')
            f, m = stub_package(source, pkg, quiet=quiet)
            total_files += f
            total_methods += m
            print(f'    → {f} files / {m} methods stubbed')
        print(f'\n  ✦ Total: {total_files} files / {total_methods} methods stubbed')
    else:
        print('\n  (no packages to stub)')

    # ── Phase 2: Remove ad SDK providers from manifest ──
    providers = config.get('providers_to_remove', [])
    if providers:
        print(f'\n=== Removing {len(providers)} providers from manifest ===')
        count = remove_providers_from_manifest(source, providers)
        print(f'  → removed {count} provider entries')

    # ── Phase 3: Clean up ad-related permissions ──
    permissions = config.get('permissions_to_remove', [])
    if permissions:
        print(f'\n=== Cleaning {len(permissions)} permissions ===')
        count = clean_ad_permissions(source, permissions)
        print(f'  → removed {count} permission entries')

    print('\n✓ Done')
    return 0


if __name__ == '__main__':
    sys.exit(main())
