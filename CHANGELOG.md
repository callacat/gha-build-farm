# Changelog

All notable changes to the gha-build-farm project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **去广告版 (Remove Ads)** — new workflow `remove-ads` in `hg-mod.yml`
  - Remove ad SDKs: LuckyCat, Baidu Mobads, Sigmob, Kuaishou, Pgl
  - Remove push SDKs: Xiaomi, Huawei, Vivo, OPPO, Heytop (Honor)
  - Strip all non-essential permissions (keep only INTERNET, NETWORK/WIFI state, storage, foreground service, install packages, notifications, ByteDance account)
  - Stub ByteDance ad SDK (com.bytedance.sdk.openadsdk) — init returns no-op, app does not crash
  - Keep ByteDance push activity references (PushActivity used by app code)
  - Cleanup manifest components referencing deleted push SDK receivers/services

- **去弹窗版 (Patch)** — new workflow `patch` in `hg-mod.yml`
  - Remove forced update dialog (update domain poison, smali method NOP, Arsc string clearing)
  - Remove deer-brand (鹿属) software declaration dialog
  - Remove group chat invite dialog
  - Redirect update check domain to `127.0.0.1` (LDPlayer loopback)
  - NOP modder network connection methods
  - Disable `UpdateServiceImpl.checkUpdate()` method
  - Remove `libseccore.so` and associated smali directories

### Changed

- APK fetch: URL-specified download takes priority; falls back to release cache
- Release: versioned APK filenames with build number (`hg-remove-ads-{version}-b{build}.apk`)
- Release: `latest` tag always points to newest build; versioned tags kept for last 5 releases
- Release notes: formatted with Shanghai timezone and download links
- Notification: TG bot notification on build completion (success/failure)
- Cleanup: auto-delete old workflow runs (keep minimum 5)

### Fixed

- **去广告版**: preserve `usesCleartextTraffic=true` in manifest — HTTP danmaku streams need cleartext
- **去广告版**: keep `GET_ACCOUNTS` and `AUTHENTICATE_ACCOUNTS` permissions — ByteDance account service requires them
- **去广告版**: do not stub `TTAdSdk.init`/`TTAdManager.init` — stubbing breaks danmaku overlay
- **去弹窗版**: revert Arsc string clearing — caused blank dialog, pending reimplementation
- **去弹窗版**: repair `public.xml` invalid resource types before `apktool b` (use `fix-public-xml.py`)
- **去弹窗版**: use `aapt1` for rebuild — `aapt2` rejects ByteDance's `invalid15` resource type
- **去弹窗版**: remove `--copy-original` from apktool rebuild step
- **去弹窗版**: only poison update domain, not CDN/API endpoints
- **去弹窗版**: return false from `checkUpdate`, not return-void

## [0.1.0] - 2025-06-01

### Added

- Initial project setup with GitHub Actions build farm workflows
- `build-python-wheel` — compile PyPI source wheels with custom CFLAGS
- `build-docker` — build and push Docker images to GHCR
- `build-apt-package` — build .deb from apt source packages
- `build-reverse-tool` — compile security/reverse engineering tools
- `build-clean-apk` — LSPatch Fanqie APK build workflow
- `apk-triage` — APK decompile and triage workflow
- `apk-diff` — smali-level APK diff workflow
- reverse-skill integration for automatic GHA dispatch from security tool bootstrap

[unreleased]: https://github.com/callacat/gha-build-farm/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/callacat/gha-build-farm/releases/tag/v0.1.0
