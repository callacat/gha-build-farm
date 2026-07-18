# gha-build-farm

## 核心 Flow: hg-mod-apk

红果短剧 APK 修改，**启动前必须读** `.claude/skills/hg-mod-apk/SKILL.md`：

```
1. 决定用哪个 workflow -> analysis / remove-ads / patch
2. 确定版本 -> 从 hg-original-{version} 拉
3. 触发构建 -> gh workflow run hg-mod.yml -R callacat/gha-build-farm -f app_id=hg ...
4. 等待 -> gh run view <run-id>
5. 更新 CHANGELOG.md + BUILD_STATE.json
```

也可以用脚本一键触发：`node .github/workflows/hg-mod-pipeline.js <workflow> <version>`

## 快速命令

```bash
# 分析
gh workflow run hg-mod.yml -R callacat/gha-build-farm -f app_id=hg -f apk_url="<url>" -f workflow=analysis

# 去弹窗版
gh workflow run hg-mod.yml -R callacat/gha-build-farm -f app_id=hg -f apk_url="<url>" -f workflow=patch

# 去广告版
gh workflow run hg-mod.yml -R callacat/gha-build-farm -f app_id=hg -f apk_url="<url>" -f workflow=remove-ads

# 查看运行状态
gh run list -R callacat/gha-build-farm -w hg-mod.yml -L 3
```
