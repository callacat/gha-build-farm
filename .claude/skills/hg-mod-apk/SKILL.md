---
name: hg-mod-apk
description: 红果短剧 APK 修改流水线 — 分析/去广告版/去弹窗版 三路径，不跳步，不忘记
user-invocable: true
---

# 红果短剧 APK 修改流水线

> **铁律：每次操作必须读此文件，严格按流程走，不可跳步**

## 架构总览

```
仓库: callacat/gha-build-farm
Workflow: hg-mod.yml
路径: 3 条独立 workflow（不可混用）
  ├─ analysis     — 只分析不修改
  ├─ patch        — 去弹窗版（基于官方原版）
  └─ remove-ads   — 去广告版（基于官方原版）
```

## 触发前检查清单

启动任何 workflow 前必须确认：

```
□ app_id 是否正确（hg=红果短剧）
□ apk_url 是否指向正确的 APK 来源
  → 去弹窗/去广告：都用 hg-original-{version}/hg.apk（官方原版）
□ workflow 选择是否正确
  → analysis: 只分析代码
  → patch: 去弹窗版（去更新弹窗 + 去鹿属弹窗）
  → remove-ads: 去广告版（删SDK + 删推送 + 清权限）
```

## Pull Request 提示

所有修改都在 `main` 分支直接做，**不需要 PR**。提交前过：
```
□ 修改了什么文件？
□ 会影响哪个 workflow？（analysis / patch / remove-ads）
□ YAML 语法验证：python3 -c "import yaml; yaml.safe_load(open('.github/workflows/hg-mod.yml'))"
□ Python 脚本语法验证：python3 -c "compile(open('path').read(), 'path', 'exec')"
```

## 构建后验证清单

```
□ gh run view <run-id> -R callacat/gha-build-farm --json conclusion → "success"
□ 下载链接正确（check hg-patch-latest / hg-remove-ads-latest）
□ TG 通知已检查（可选）
□ 更新 CHANGELOG.md（如适用）
□ BUILD_STATE.json 已更新
```

## Release 命名规范

### 去弹窗版（workflow=patch）
| 项 | 格式 |
|----|------|
| Latest Release | `hg-patch-latest` |
| Versioned Release | `hg-patch-v{version}-b{run_number}` |
| APK 文件名 | `hg-patch-{version}-b{run_number}.apk` |

### 去广告版（workflow=remove-ads）
| 项 | 格式 |
|----|------|
| Latest Release | `hg-remove-ads-latest` |
| Versioned Release | `hg-remove-ads-v{version}-b{run_number}` |
| APK 文件名 | `hg-remove-ads-{version}-b{run_number}.apk` |

### 原始版缓存（hg-original-*）
| 项 | 格式 |
|----|------|
| Cache Tag | `hg-original-{version}` |
| APK 文件名 | `hg.apk` |

## 状态持久化

每次构建完成后，更新 `BUILD_STATE.json`：
```json
{
  "latest_remove_ads": {"version": "7.2.8.32", "run_id": 12345, "status": "success"},
  "latest_patch": {"version": "7.2.8.32", "run_id": 12345, "status": "success"}
}
```

## ⛔ 不可跳步骤

| 禁止项 | 原因 |
|--------|------|
| 不验证 YAML 就 push | YAML 语法错 → workflow 启动失败 |
| 不查 run 结果就说完成了 | 可能是 in_progress 或失败 |
| 用错 apk_url | 版本不对 → 白构建 |
| 改了 workflow 不更新 CHANGELOG | 无记录 → 不可追溯 |
| 不更新 BUILD_STATE.json | 下次会话不知道上次状态 |
