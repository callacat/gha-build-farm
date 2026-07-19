#!/usr/bin/env python3
"""
hg-find-obfuscated-ad-code.py — Comprehensive ad code location finder.

Searches through jadx Java decompilation output to identify:
1. Obfuscated classes (single-letter directory names in com/) that reference ad SDKs
2. App-specific ad wrapper code (com/dragon/read/ad/)
3. Classes that call bytedance openadsdk/Pangle APIs
4. Methods that invoke loadAd/showAd on ad objects
5. The real ad package names post-R8 obfuscation

Usage:
  python3 hg-find-obfuscated-ad-code.py --jadx-dir /tmp/jadx_out [--output /tmp/analysis.md]
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


# ── Known ad SDK keywords in Java source (class names, methods, strings) ──
AD_SDK_KEYWORDS: List[str] = [
    # Pangle / TTAdSdk API
    "TTAdSdk", "TTAdSdk", "TTAdNative", "TTAdManager",
    "TTBannerAd", "TTInterstitialAd", "TTRewardVideoAd",
    "TTFullScreenVideoAd", "TTSplashAd", "TTFeedAd",
    "TTNativeAd", "TTVideoAd", "TTDrawFeedAd",
    "TTAdConstant", "TTAdDislike", "TTAppDownloadListener",
    "AdSlot", "AdSlotBuilder",
    "openadsdk", "PangleAd", "pangle",
    "com.bytedance.sdk.openadsdk",
    "com.bytedance.pangle",
    # Ad loading / display
    "loadAd", "showAd", "showBannerAd", "showInterstitialAd",
    "showRewardVideoAd", "showSplashAd", "showFeedAd",
    "loadBannerAd", "loadInterstitialAd",
    "loadRewardVideoAd", "loadSplashAd", "loadFeedAd",
    "setAdListener", "setAdShowListener",
    # App-side ad model/entity
    "AdItem", "AdData", "AdModel", "AdRequestManager",
    "AdResponse", "AdLoader", "AdUtils",
    "TTAdSdk", "TTAdManagerHolder",
    # Mediation
    "Gromore", "gromore", "mediation",
    # Also check string constants
    "csj", "pangle_sdk", "tt_ad",
]


def find_ad_references(jadx_sources: Path) -> Dict[str, List[str]]:
    """Search all Java files in jadx output for ad SDK references.

    Returns dict of {keyword: [file paths that contain it]}
    Skips known third-party packages (androidx, kotlin, okhttp3, etc.)
    """
    skip_dirs = {
        "androidx", "kotlin", "kotlinx", "okhttp3", "org",
        "coil3", "okio",
    }

    results: Dict[str, List[str]] = defaultdict(list)

    for root, dirs, files in os.walk(jadx_sources):
        # Check if this is a directory tree we should skip
        rel = Path(root).relative_to(jadx_sources)
        parts = set(str(rel).split(os.sep))
        if parts & skip_dirs:
            continue

        for fname in files:
            if not fname.endswith('.java'):
                continue
            fpath = Path(root) / fname
            try:
                text = fpath.read_text('utf-8', errors='replace')
            except Exception:
                continue

            for keyword in AD_SDK_KEYWORDS:
                if keyword in text:
                    rel_path = str(fpath.relative_to(jadx_sources))
                    results[keyword].append(rel_path)

    return results


def classify_obfuscated_dirs(jadx_sources: Path) -> Dict[str, int]:
    """Classify top-level dirs under com/ as obfuscated or not.

    R8 obfuscation produces single-letter or short alphanumeric directory names.
    Returns dict of {dir_name: file_count}.
    """
    com_dir = jadx_sources / "com"
    if not com_dir.is_dir():
        return {}

    counts: Dict[str, int] = {}
    obfuscated: Dict[str, int] = {}

    for entry in sorted(com_dir.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        java_files = len(list(entry.rglob("*.java")))
        counts[name] = java_files

        # Obfuscation heuristic: short name (1-3 chars), starts with lowercase
        # OR matches pattern like a01, b71, etc.
        is_obfuscated = (
            len(name) <= 3 and (
                name.islower() or name[0].islower()
            )
        ) or bool(re.match(r'^[a-z][a-z0-9]{0,3}$', name))

        # Also: uppercase single letter (J, E, etc.) is obfuscated
        is_obfuscated = is_obfuscated or (len(name) == 1 and name.isupper() and name not in ("C", "S", "I"))

        if is_obfuscated:
            obfuscated[name] = java_files

    print(f"\n=== Obfuscated directories under com/ ({len(obfuscated)} found ===")
    for name, count in sorted(obfuscated.items(), key=lambda x: -x[1])[:30]:
        print(f"  {name}: {count} files")
    print(f"  ... ({len(obfuscated)} total obfuscated packages)")

    return counts


def find_ad_referencing_obfuscated(jadx_sources: Path, search_terms: List[str] = None) -> Dict[str, Set[str]]:
    """Find obfuscated classes (single-letter dirs under com/) that reference ad SDKs.

    Returns dict of {obfuscated_package: set(class_names)}.
    Only searches files in obfuscated directories.
    Skips known non-ad directories like androidx, kotlin, etc.
    """
    skip_dirs = {
        "androidx", "kotlin", "kotlinx", "okhttp3", "org",
        "coil3", "okio",
    }

    # Define ad-related search terms for obfuscated-to-ad relationships
    if search_terms is None:
        search_terms = [
            "openadsdk", "TTAdSdk", "TTAdNative", "AdSlot",
            "PangleAd", "pangle", "loadAd", "showAd",
            "com.bytedance.sdk.openadsdk",
            "com.bytedance.pangle",
            "TTAdManager", "TTBannerAd", "TTInterstitialAd",
            "TTRewardVideoAd", "TTFullScreenVideoAd",
            "TTSplashAd", "TTFeedAd", "TTNativeAd",
            "setAdListener", "setAdShowListener",
        ]

    obfuscated_refs: Dict[str, Set[str]] = defaultdict(set)

    for root, dirs, files in os.walk(jadx_sources):
        rel = Path(root).relative_to(jadx_sources)
        parts = str(rel).split(os.sep)

        # Skip non-obfuscated and known library dirs
        if len(parts) < 3:
            continue
        if parts[0] != "com":
            continue
        pkg_name = parts[1]

        # Check if it's obfuscated
        is_obfuscated = (
            (len(pkg_name) <= 3 and (pkg_name.islower() or pkg_name[0].islower())) or
            bool(re.match(r'^[a-z][a-z0-9]{0,3}$', pkg_name)) or
            (len(pkg_name) == 1 and pkg_name.isupper() and pkg_name not in ("C", "S", "I"))
        )
        if not is_obfuscated:
            continue
        if parts[1] in skip_dirs:
            continue

        for fname in files:
            if not fname.endswith('.java'):
                continue
            fpath = Path(root) / fname
            try:
                text = fpath.read_text('utf-8', errors='replace')
            except Exception:
                continue

            for term in search_terms:
                if term in text:
                    obfuscated_refs[pkg_name].add(fname.replace('.java', ''))
                    break

    return obfuscated_refs


def find_app_ad_wrapper_classes(jadx_sources: Path) -> List[str]:
    """Find com.dragon.read.ad wrapper/adapter classes that likely bridge to ad SDKs."""
    ad_dir = jadx_sources / "com" / "dragon" / "read" / "ad"
    if not ad_dir.is_dir():
        return []

    results = []
    for java_file in sorted(ad_dir.rglob("*.java")):
        rel = java_file.relative_to(jadx_sources)
        try:
            text = java_file.read_text('utf-8', errors='replace')
        except Exception:
            continue

        # Check if this file references any obfuscated ad SDK
        results.append({
            'path': str(rel),
            'references_sdk': any(kw in text for kw in AD_SDK_KEYWORDS),
            'has_load_show': bool(re.search(r'\b(loadAd|showAd|loadBanner|showBanner|loadSplash|showSplash)\b', text)),
            'has_init': 'onCreate' in text or 'init' in text or 'TTAdSdk' in text,
            'is_interface': 'interface' in text,
            'methods': extract_method_names(text),
        })

    return results


def extract_method_names(java_text: str) -> List[str]:
    """Extract method declarations from Java text."""
    methods = re.findall(r'(?:public|private|protected)\s+(?:static\s+)?[\w<>[\]]+\s+(\w+)\s*\(', java_text)
    return methods


def analyze_ad_dragon_read_packages(jadx_sources: Path) -> None:
    """Comprehensive analysis of com.dragon.read ad-related code."""
    print("\n" + "=" * 70)
    print("ANALYSIS: com.dragon.read ad packages")
    print("=" * 70)

    ad_base = jadx_sources / "com" / "dragon" / "read"
    if not ad_base.is_dir():
        print("  com.dragon.read not found!")
        return

    # Walk all files under com/dragon/read
    for root, dirs, files in os.walk(ad_base):
        for fname in files:
            if not fname.endswith('.java'):
                continue
            fpath = Path(root) / fname
            try:
                text = fpath.read_text('utf-8', errors='replace')
            except Exception:
                continue

            rel = fpath.relative_to(jadx_sources)

            # Check for ad SDK references
            sdk_refs = [kw for kw in AD_SDK_KEYWORDS[:30] if kw in text]

            # Check for reflection calls to bytedance ad SDK
            reflection_refs = re.findall(
                r'Class\.forName\("com\.(?:bytedance|ss)\.[^"]*ad[^"]*"\)',
                text
            ) or re.findall(
                r'Class\.forName\("com\.bytedance\.[^"]+"\)',
                text
            )

            if sdk_refs or reflection_refs or ('loadAd' in text and 'com.dragon' not in text):
                if sdk_refs or reflection_refs:
                    print(f"\n  📄 {rel}")
                    if sdk_refs:
                        print(f"     SDK refs: {sdk_refs[:5]}")
                    if reflection_refs:
                        print(f"     Reflection: {reflection_refs}")
                    methods = extract_method_names(text)
                    if methods:
                        print(f"     Methods: {methods[:10]}")


def analyze_pangle_sdk_structure(jadx_sources: Path) -> None:
    """Analyze what remains of the bytedance Pangle SDK post-R8."""
    print("\n" + "=" * 70)
    print("ANALYSIS: Surviving bytedance SDK package structure")
    print("=" * 70)

    bytedance_base = jadx_sources / "com" / "bytedance"
    if not bytedance_base.is_dir():
        print("  com/bytedance not found!")
        return

    # Count files per sub-package
    for entry in sorted(bytedance_base.iterdir()):
        if not entry.is_dir():
            continue
        java_count = len(list(entry.rglob("*.java")))
        if java_count > 0:
            print(f"  com/bytedance/{entry.name}: {java_count} files")
            # List class names for small packages
            if java_count <= 10:
                for jf in sorted(entry.rglob("*.java")):
                    print(f"    - {jf.name}")

    # Check ss/ (also bytedance)
    ss_base = jadx_sources / "com" / "ss"
    if ss_base.is_dir():
        print("\n  === com/ss (socialbase/sdk) ===")
        for entry in sorted(ss_base.iterdir()):
            if not entry.is_dir():
                continue
            java_count = len(list(entry.rglob("*.java")))
            if java_count > 0:
                print(f"  com/ss/{entry.name}: {java_count} files")


def find_obfuscated_packages_with_ad_imports(jadx_sources: Path) -> List[Dict]:
    """Find packages obfuscated by R8 that import ad SDK classes.

    This looks for Java import statements referencing com.bytedance.sdk.openadsdk
    in obfuscated classes (since R8 may still leave some import statements).
    """
    results = []

    for root, dirs, files in os.walk(jadx_sources):
        for fname in files:
            if not fname.endswith('.java'):
                continue
            fpath = Path(root) / fname
            try:
                first_lines = fpath.read_text('utf-8', errors='replace').split('\n')[:50]
            except Exception:
                continue

            # Check imports
            imports = [l for l in first_lines if l.startswith('import ') and
                      ('bytedance' in l or 'ss.android' in l)]

            if imports:
                rel = fpath.relative_to(jadx_sources)
                name = str(rel)
                if 'com/dragon/read' not in name and 'com/bytedance' not in name:
                    results.append({
                        'file': name,
                        'imports': imports[:10],
                    })

    return results


def generate_report(jadx_dir: Path, output_path: str | None = None) -> str:
    """Generate comprehensive analysis report."""
    jadx_sources = jadx_dir / "sources"

    lines: List[str] = []
    def out(s: str = "") -> None:
        lines.append(s)
        print(s)

    out("=" * 70)
    out("HG ANALYSIS REPORT: Ad Code Location Analysis")
    out("Version: 7.2.7.32 (jadx decompilation)")
    out("=" * 70)

    # 1. Basic structure
    out("\n## 1. Overall Structure")
    out(f"\nTotal Java files: {len(list(jadx_sources.rglob('*.java')))}")

    # 2. Obfuscated vs known folders
    out("\n## 2. R8 Obfuscation Impact on Packages")

    com_dir = jadx_sources / "com"
    known_dirs = {"bytedance", "dragon", "ss", "tencent", "squareup", "google", "airbnb", "facebook", "github", "google"}

    obfuscated_count = 0
    known_count = 0
    for entry in sorted(com_dir.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        is_obf = (len(name) <= 3 and (name.islower() or name[0].islower())) or \
                 bool(re.match(r'^[a-z][a-z0-9]{0,3}$', name)) or \
                 (len(name) == 1 and name.isupper() and name not in ("C", "S", "I"))
        if is_obf and name not in known_dirs:
            obfuscated_count += 1
        elif name not in known_dirs and len(name) <= 4:
            obfuscated_count += 1

    out(f"  Known packages: {len(list(com_dir.iterdir())) - obfuscated_count}")
    out(f"  Obfuscated packages (R8): ~{obfuscated_count}")

    # 3. Obfuscated classes that reference Pangle
    obfuscated_refs = find_ad_referencing_obfuscated(jadx_sources)
    if obfuscated_refs:
        out(f"\n## 3. Obfuscated Packages Referencing Ad SDKs ({len(obfuscated_refs)})")
        for pkg, classes in sorted(obfuscated_refs.items()):
            out(f"  com/{pkg}/ → {len(classes)} classes reference ad SDK")
            # Show the actual class names
            for cls in sorted(classes)[:5]:
                out(f"    - {cls}")
            if len(classes) > 5:
                out(f"    ... and {len(classes)-5} more")

    # 4. Pangle SDK structure
    out("\n## 4. Surviving Pangle / bytedance Ad SDK Structure")
    bytedance_count = 0
    for entry in sorted((jadx_sources / "com" / "bytedance").iterdir()):
        if not entry.is_dir():
            continue
        java_count = len(list(entry.rglob("*.java")))
        if java_count > 0:
            bytedance_count += java_count
            out(f"  com/bytedance/{entry.name}: {java_count} files")
    out(f"\n  Total surviving bytedance files: {bytedance_count}")
    out(f"  (Most of the ~8500 Pangle SDK classes were R8-obfuscated)")

    # 5. Dragon Read ad code
    out("\n## 5. com.dragon.read Ad-Related Code")
    analyze_ad_dragon_read_packages(jadx_sources)

    # 6. smali stub mapping
    out("\n## 6. Mapping to Current smali-stub Strategy")

    # For each package in ad-removal.json, find the corresponding
    # obfuscated class names that reference it
    ad_packages = [
        "com/bytedance/sdk/openadsdk",
        "com/bytedance/pangle",
        "com/bytedance/sdk/component",
        "com/bytedance/sdk/bridge",
        "com/bytedance/sdk/dp",
        "com/bytedance/sdk/gromore",
        "com/bytedance/sdk/panglelog",
        "com/bytedance/sdk/download",
        "com/bytedance/sdk/activity",
        "com/bytedance/sdk/adbt",
        "com/bytedance/sdk/ade",
        "com/bytedance/sdk/mob",
        "com/bytedance/sdk/static",
        "com/bytedance/sdk/te",
        "com/bytedance/sdk/live",
        "com/bytedance/sdk/plugin",
        "com/bytedance/sdk/qq",
        "com/bytedance/sdk/wx",
        "com/bytedance/sdk/we",
        "com/bytedance/adlive",
        "com/bytedance/mob",
    ]

    out("\nPackages being stubbed in ad-removal.json:")
    for pkg in ad_packages:
        # Count matching files in jadx
        full_path = jadx_sources / pkg.replace("/", os.sep)
        if full_path.exists():
            count = len(list(full_path.rglob("*.java")))
            out(f"  ✅ {pkg}: {count} files FOUND")
        else:
            out(f"  ❌ {pkg}: NOT FOUND in jadx output (R8-merged)")

    out("\n## 7. Key Conclusions")

    # Write findings to output file if provided
    report = "\n".join(lines)
    if output_path:
        Path(output_path).write_text(report, encoding='utf-8')
        print(f"\nReport written to: {output_path}")

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find ad code locations in R8-obfuscated jadx output"
    )
    parser.add_argument("--jadx-dir", required=True,
                        help="Path to jadx output directory (containing sources/)")
    parser.add_argument("--output", default="/tmp/direction1-findings.txt",
                        help="Output report file path")
    parser.add_argument("--api", action="store_true",
                        help="Search for API-level ad SDK references in obfuscated code")
    args = parser.parse_args()

    jadx_dir = Path(args.jadx_dir)
    if not (jadx_dir / "sources").is_dir():
        print(f"Error: {jadx_dir}/sources not found")
        return 1

    generate_report(jadx_dir, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
