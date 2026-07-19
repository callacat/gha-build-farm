#!/usr/bin/env python3
"""
hg-stub-using-jadx.py — Generate precise smali stub targets using jadx decompilation info.

Instead of blindly stubbing packages by name (which fails because R8 merged them),
this script uses jadx output to:

1. Find the actual obfuscated package names for ad SDK classes
2. Find the app-level ad wrapper classes that bridge to the SDK
3. Generate a precise list of smali directories to stub

Usage:
  # Generate ad SDK stub targets
  python3 hg-stub-using-jadx.py --jadx-dir /tmp/jadx_out --mode find-ad-targets

  # Generate stub for a specific set of obfuscated packages
  python3 hg-stub-using-jadx.py --jadx-dir /tmp/jadx_out --mode gen-stub-list

  # Full report
  python3 hg-stub-using-jadx.py --jadx-dir /tmp/jadx_out --mode report
"""

from __future__ import annotations
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple


# ── Known ad SDK packages (the classes R8 preserves) ──
SURVIVING_AD_PACKAGES = [
    "com/bytedance/admetaversesdk",       # New Pangle API layer (31 files)
    "com/bytedance/reader_ad",            # Reader-specific ad module (38 files)
    "com/bytedance/tomato",               # Ad feature module (99 files, banner/reward/onestop)
    "com/bytedance/alliance",             # Cross-app ad alliance (37 files)
    "com/bytedance/sdk/adinnovation",     # Ad innovation SDK
    "com/bytedance/sdk/openadsdk",        # Only 7 files survive (playable)
    "com/bytedance/sdk/bridge",           # Bridge SDK (35 files)
    "com/bytedance/sdk/mobiledata",       # Mobile data SDK
    "com/bytedance/sdk/bytebridge",       # Byte bridge
    "com/bytedance/sdk/open",             # Open SDK (douyin/aweme/tt)
    "com/bytedance/sdk/xbridge",          # XBridge SDK
    "com/bytedance/ad",                   # Ad common (8 files)
    "com/bytedance/adarchitecture",       # Ad architecture (3 files)
    "com/bytedance/reader_ad",            # Reader ad (38 files)
    "com/bytedance/sdk/account",          # Account SDK
    "com/bytedance/common_ad_rifle_interface",  # Ad rifle
    "com/ss/android/ad",                 # Socialbase ad lynx
    "com/ss/android/downloadad",         # Download ad
    "com/ss/android/downloadlib",        # Download library
    "com/ss/android/excitingvideo",      # Exciting video ad
]

# ── App-side ad code that bridges to SDK ──
BRIDGE_PACKAGES = {
    "com/dragon/read/ad": "App ad wrapper layer (~150 files across 30 subdirs)",
    "com/dragon/read/reader/ad": "Reader ad integration",
    "com/dragon/read/base/ad": "Base ad module",
    "com/dragon/read/base/ssconfig": "SS config for ads (models, templates, settings)",
    "com/dragon/read/rpc/model": "RPC models with ad fields (Ad, BannerResource, etc.)",
    "com/dragon/read/nonstandard/ad": "Nonstandard ad config",
    "com/dragon/read/component/biz": "Business component ad deps",
    "com/dragon/read/story/ad": "Story ad module",
    "com/dragon/read/plugin/common": "Plugin common ad APIs",
}


def find_jadx_sources(jadx_dir: Path) -> Path:
    """Find the sources directory containing Java decompiled files."""
    sources = jadx_dir / "sources"
    if sources.is_dir():
        return sources
    # jadx may output directly
    for d in jadx_dir.iterdir():
        if d.is_dir() and list(d.rglob("*.java")):
            return d
    return jadx_dir


def find_ad_stub_targets(jadx_sources: Path) -> Dict[str, List[str]]:
    """Find all Java classes that reference Pangle/CSJ ad SDKs.

    Returns dict of {package_name: [class_files_that_reference_ad]}.
    Uses multiple search strategies:
    - Import statements for bytedance ad SDKs
    - Method calls to ad-related APIs
    - String constants containing SDK identifiers
    """
    ad_keywords = [
        "admetaverse", "TTAdSdk", "TTAdManager", "TTAdNative",
        "AdSlot", "PangleAd", "pangle", "openadsdk",
        "com.bytedance.sdk.openadsdk", "com.bytedance.pangle",
        "com.ss.android.excitingvideo",
        "admetaversesdk.banner.components",
    ]

    # File-level call patterns
    call_patterns = [
        r'\.loadAd\s*\(',
        r'TTAdSdk\s*\.',
        r'TTAdNative\s*\.',
        r'TTAdManager\s*\.',
        r'new\s+AdSlot\s*\.',
        r'AdSlotBuilder\s*\(',
    ]

    results: Dict[str, List[str]] = defaultdict(list)

    # Strategy 1: Walk all source files
    for root, dirs, files in os.walk(jadx_sources):
        rel = Path(root).relative_to(jadx_sources)
        parts = str(rel).split(os.sep)

        for fname in files:
            if not fname.endswith('.java'):
                continue
            fpath = Path(root) / fname
            try:
                text = fpath.read_text('utf-8', errors='replace')
            except Exception:
                continue

            # Check for ad SDK references
            has_ref = False
            for kw in ad_keywords:
                if kw in text:
                    has_ref = True
                    break

            if not has_ref:
                # Check call patterns
                for pat in call_patterns:
                    if re.search(pat, text):
                        has_ref = True
                        break

            if not has_ref:
                continue

            # Determine package
            pkg = "unknown"
            if len(parts) >= 2:
                pkg = parts[0]
                if len(parts) >= 3:
                    pkg = f"{parts[0]}/{parts[1]}"

            rel_path = str(rel)
            results[pkg].append(rel_path)

    return results


def gen_smali_stub_list(jadx_sources: Path, ad_config: dict | None = None) -> List[str]:
    """Generate a list of smali directories to stub based on jadx analysis.

    Returns list of smali paths relative to apktool_out/smali*.
    """
    targets = []

    # Phase 1: Include surviving ad SDK packages
    for pkg in SURVIVING_AD_PACKAGES:
        pkg_path = pkg.replace("/", os.sep)
        pkg_dir = jadx_sources / pkg_path
        if pkg_dir.exists():
            file_count = len(list(pkg_dir.rglob("*.java")))
            targets.append({
                "package": pkg,
                "reason": "Surviving Pangle/CSJ ad SDK package",
                "file_count": file_count,
                "class_names": [f.stem for f in pkg_dir.rglob("*.java")][:5],
            })

    # Phase 2: Find ad references in obfuscated packages
    obfuscated_refs = find_ad_references_in_obfuscated(jadx_sources)
    targets.extend(obfuscated_refs)

    return targets


def find_ad_references_in_obfuscated(jadx_sources: Path) -> List[dict]:
    """Find obfuscated packages under com/ that reference ad SDKs."""
    results = []

    ad_kw = [
        "admetaverse", "openadsdk", "AdSlot", "TTAdSdk",
        "loadAd", "showAd", "com.bytedance.sdk",
        "com.ss.android.ad", "PangleAd",
    ]

    for root, dirs, files in os.walk(jadx_sources):
        rel = Path(root).relative_to(jadx_sources)
        parts = str(rel).split(os.sep)

        if len(parts) < 2 or parts[0] != "com":
            continue

        pkg_name = parts[1]
        if len(pkg_name) > 3:
            continue
        if pkg_name in ("dragon", "bytedance", "ss", "androidx", "kotlin", "kotlinx"):
            continue
        if not (pkg_name.islower() or re.match(r'^[a-z][a-z0-9]{0,3}$', pkg_name)):
            continue

        for fname in files:
            if not fname.endswith('.java'):
                continue
            fpath = Path(root) / fname
            try:
                text = fpath.read_text('utf-8', errors='replace')
            except Exception:
                continue

            for kw in ad_kw:
                if kw in text:
                    results.append({
                        "package": f"com/{pkg_name}",
                        "file": str(fpath.relative_to(jadx_sources)),
                        "keyword": kw,
                    })
                    break

    return results


def generate_report(jadx_sources: Path) -> str:
    """Generate comprehensive ad code location report."""
    lines = []
    def out(s=""):
        lines.append(s)

    out("# HG Ad Code Location Report (v7.2.7.32)")
    out("")
    out("## Key Finding: R8 Obfuscation Strategy")
    out("")
    out("R8 performed aggressive tree-shaking and obfuscation on the Pangle/CSJ ad SDK.")
    out("Most ad SDK classes were:")
    out("1. Obfuscated into single-letter directory names under `com/` (e.g., `com/a/*`)")
    out("2. Merged into `com/dragon/` (19169 files)")
    out("3. Merged into `com/bytedance/` (13703 files)")
    out("4. Merged into `com/ss/` (2273 files)")
    out("")
    out("### Packages from ad-removal.json that DON'T EXIST in jadx output:")
    out("")
    for pkg in [
        "com/bytedance/pangle",
        "com/bytedance/sdk/component",
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
    ]:
        pkg_dir = jadx_sources / pkg.replace("/", os.sep)
        if not pkg_dir.exists():
            out(f"- `{pkg}` — NOT FOUND (R8-merged/obfuscated)")

    out("")
    out("## Surviving Ad SDK Packages")
    out("")
    out("The following ad SDK packages survived R8 tree-shaking:")
    out("")
    existing = []
    for pkg in SURVIVING_AD_PACKAGES:
        pkg_dir = jadx_sources / pkg.replace("/", os.sep)
        if pkg_dir.exists():
            count = len(list(pkg_dir.rglob("*.java")))
            existing.append((pkg, count))

    for pkg, count in sorted(existing, key=lambda x: -x[1]):
        out(f"| {pkg} | {count} files | Surviving ad package |")

    out("")
    out("## App-Side Ad Wrapper Code (com.dragon.read)")
    out("")
    out("The app wraps Pangle/CSJ through several adapter layers:")
    out("")
    out("| Directory | Description |")
    out("|-----------|-------------|")
    out("| `com/dragon/read/ad/` | Main ad service layer (~150 files) |")
    out("| `com/dragon/read/reader/ad/` | Reading flow ad integration |")
    out("| `com/dragon/read/ad/tomato/` | Tomato SDK bridge |")
    out("| `com/dragon/read/ad/onestop/` | One-stop ad management |")
    out("| `com/dragon/read/ad/banner/` | Banner ads |")
    out("| `com/dragon/read/ad/splash/` | Splash ads |")
    out("| `com/dragon/read/nonstandard/ad/` | Nonstandard ad config |")
    out("| `com/dragon/read/rpc/model/` | RPC models with ad data |")
    out("| `com/dragon/read/story/ad/` | Story module ads |")
    out("")
    out("### Key Ad API Interfaces: reference 'csj' or 'admetaversesdk'")
    out("")
    csj_refs = []
    for root, dirs, files in os.walk(jadx_sources):
        for f in files:
            if f.endswith('.java'):
                fp = Path(root) / f
                try:
                    t = fp.read_text('utf-8', errors='replace')
                except:
                    continue
                if 'csj' in t.lower() or 'admetaverse' in t:
                    rel = fp.relative_to(jadx_sources)
                    if 'com/dragon/read' in str(rel) or 'com/bytedance/tomato' in str(rel):
                        csj_refs.append(str(rel))
                if len(csj_refs) >= 30:
                    break
        if len(csj_refs) >= 30:
            break

    for ref in sorted(csj_refs)[:30]:
        out(f"- `{ref}`")

    out("")
    out("## How the App Loads Ads (Contract)")
    out("")
    out("The actual Pangle SDK classes are invoked via:")
    out("")
    out("1. **ServiceManager pattern**: `com.bytedance.news.common.service.manager.ServiceManager`")
    out("   - Ad feature services registered with `IRewardResourcePreloadService` etc.")
    out("   - App implements interfaces like `IReaderAdSettingsConfigService`")
    out("")
    out("2. **Tomato SDK bridge**: `com/bytedance/tomato/`")
    out("   - `com.bytedance.tomato.api.*` — interfaces for reward, settings, common")
    out("   - `com.bytedance.tomato.reward.entity.*` — reward ad entities")
    out("   - `com.bytedance.tomato.banner.*` — banner ad API")
    out("   - App implements these interfaces at `com/dragon/read/ad/tomato/*/impl/`")
    out("")
    out("3. **admetaverse SDK**: `com/bytedance/admetaversesdk/`")
    out("   - `AdModel` entity used across the app's ad flow")
    out("   - `AdModule` enum: `AdModule.CSJ`, `AdModule.BANNER`, etc.")
    out("")
    out("4. **Reader_banner**: `com/bytedance/reader_ad/banner_ad/`")
    out("   - `ReaderBannerAdFacade` — facade for banner ad loading")
    out("   - `ReaderBannerRefreshStrategy` — refresh strategy")
    out("   - Config models: `BannerAdConfig`, `CommonAdConfig`, `ReaderFeedConfig`")
    out("")
    out("## Recommended Stub Targets")
    out("")
    out("For maximum ad removal, stub the following packages (by smali directory):")
    out("")
    out("### Tier 1: Ad SDK Exposed Classes (definitely stub)")
    out("")
    for pkg in existing:
        out(f"- `{pkg}` ({pkg.count} files)")

    out("")
    out("### Tier 2: App-Specific Ad Implementation (stub to break integration)")
    out("")
    out("- `com/dragon/read/ad/tomato/impl/` — App's tomato SDK implementations")
    out("- `com/dragon/read/ad/onestop/` — One-stop ad management")
    out("- `com/dragon/read/reader/ad/readflow/` — Read flow ad integration")
    out("- `com/dragon/read/nonstandard/ad/` — Nonstandard ad config")

    report = "\n".join(lines)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate ad stub targets using jadx analysis"
    )
    parser.add_argument("--jadx-dir", required=True,
                        help="Path to jadx output directory")
    parser.add_argument("--mode", default="report",
                        choices=["report", "find-ad-targets", "gen-stub-list"],
                        help="Analysis mode")
    parser.add_argument("--output", default="/tmp/ad-stub-targets.json",
                        help="Output path for JSON stub list")
    args = parser.parse_args()

    jadx_dir = Path(args.jadx_dir)
    jadx_sources = find_jadx_sources(jadx_dir)
    print(f"Using jadx sources: {jadx_sources}")
    print(f"Total Java files: {len(list(jadx_sources.rglob('*.java')))}")

    if args.mode == "report":
        # Generate report in text format
        report = generate_report(jadx_sources)

        # Also produce machine-readable output
        stub_targets = gen_smali_stub_list(jadx_sources)

        with open(args.output, 'w') as f:
            json.dump(stub_targets, f, indent=2, ensure_ascii=False)
        print(f"\nAd stub targets written to: {args.output}")

        # Write the report
        report_path = str(args.output).replace(".json", "-report.md")
        Path(report_path).write_text(report)
        print(f"Report written to: {report_path}")
        print()
        print(report)

    elif args.mode == "find-ad-targets":
        targets = find_ad_stub_targets(jadx_sources)
        print(f"\n=== Ad-referencing packages ({len(targets)}) ===")
        for pkg, files in sorted(targets.items()):
            print(f"  {pkg}: {len(files)} files")
        Path(args.output).write_text(
            json.dumps(dict(targets), indent=2, ensure_ascii=False)
        )

    elif args.mode == "gen-stub-list":
        targets = gen_smali_stub_list(jadx_sources)
        Path(args.output).write_text(
            json.dumps(targets, indent=2, ensure_ascii=False)
        )
        print(f"\n=== Stub targets ({len(targets)}) ===")
        for t in targets:
            print(f"  {t}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
