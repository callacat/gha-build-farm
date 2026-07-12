# 红果短剧第三方修改版强制更新弹窗诊断报告

**日期**: 2026-07-12  
**项目**: gha-build-farm/红果短剧去更新  
**诊断模型**: Codex (Backend) + Antigravity (Frontend, 部分)  
**状态**: ✅ 诊断完成，待实施验证

---

## 问题症状

- **现象**: 启动后立即出现强制更新弹窗，按钮为"立即更新"，无法关闭，必须更新或退出应用
- **域名毒化无效**: 已毒化 8 个字节跳动域名（包括 `remote.oneseeker.top/appUpdate`）后弹窗仍出现
- **搜索困难**: 
  - 全局 smali 搜索"立即更新"无命中
  - URL 定位在 `MainFragmentActivity.smali:56416`，但附近 1000 行无 `AlertDialog` 构建代码
  - 文本可能来自资源 ID、服务端配置、加密字符串或自定义组件

---

## 诊断假设（按可能性排序）

### 假设1: 自定义 Dialog/队列弹窗系统 ⭐⭐⭐⭐⭐
**可能性: 最高**

#### 触发机制分析
- 启动阶段（`Application.onCreate` / `SplashActivity` / 首屏 Activity）
- 红果/番茄系应用自带 Pop/Queue 弹窗框架
- 消费"强制升级"配置后调用自定义 `Dialog.show()`
- 不依赖当前网络请求结果（解释了域名毒化无效）

#### 历史命中证据
历史分析曾在以下位置定位到强制更新链路：
- `AbsQueueDialog.show()` — 队列弹窗基类
- `force_upgrade_dialog` — 强制升级弹窗标识
- `UpdateProgressActivity` — 更新进度 Activity
- `LuckyDogLowUpdateDialog` — 具体弹窗实现类
- `PushImpl.forceUpdate` — 推送触发强制更新

真实混淆位置（非原始类名）：
- `uc/e.java`
- `od/b.java`
- `com/tw.java`
- `com/C6665qf.java`

所有位置均含 `setCancelable(false)` 调用。

#### UI 实现方式
自定义 `Dialog` 子类，特征：
- `setCancelable(false)` — 禁用返回键关闭
- `setCanceledOnTouchOutside(false)` — 禁用外部点击关闭
- 按钮文案可能动态注入（解释了搜索无明文命中）

#### 搜索建议
```bash
# 1. 搜索弹窗展示调用
rg -n -C 8 'AbsQueueDialog;->show|->show\(\)V|setCancelable\(Z\)V|setCanceledOnTouchOutside\(Z\)V' /tmp/apktool_out/smali*

# 2. 搜索启动入口
rg -n 'Application;->onCreate|SplashActivity|MainActivity|AbsQueueDialog;->show' /tmp/apktool_out/smali*

# 3. 定位强制更新配置消费点
rg -n -C 6 'force_upgrade|forceUpdate|ForceUpdate|needUpdate|checkUpdate' /tmp/apktool_out/smali*
```

#### Patch 方案

**首选: 短路 `show()` 方法**
```smali
.method ... show...(...)V
    .locals 0
    return-void
.end method
```

**备选: NOP 调用点**
```smali
# 原始
invoke-virtual {vX}, Landroid/app/Dialog;->show()V

# patch
nop
```

**处理返回值的情况**
```smali
# 原始
invoke-virtual {vX}, Landroid/app/AlertDialog$Builder;->show()Landroid/app/AlertDialog;
move-result-object vY

# patch
nop
const/4 vY, 0x0
```

---

### 假设2: 本地硬编码版本判断 ⭐⭐⭐⭐⭐
**可能性: 高**

#### 根因分析
域名毒化只影响新网络请求，但如果判断逻辑为：
- APK 内硬编码最低版本号
- 从 `SharedPreferences` / `assets` / 加密配置读取
- 当前 `versionCode=72732` < 目标版本 → 直接弹窗

则毒化无效。

#### 证据支持
- 毒化 `remote.oneseeker.top/appUpdate` 后弹窗仍出现
- 第三方修改版常将版本判断写死（简单粗暴的实现方式）
- 搜索"立即更新"无明文命中 → UI 文案未必来自接口响应

#### 搜索建议
```bash
# 搜索版本判断和强制字段
rg -n -C 6 'getVersionCode|getLongVersionCode|versionCode|forceUpdate|ForceUpdate|needUpdate|checkUpdate|upgrade|update' /tmp/apktool_out/smali*
```

#### Patch 方案

**方案1: 修改判断方法返回值**
```smali
# 对 isNeedUpdate / forceUpdate / checkUpdate 返回 Z 的方法
.method ... (...)Z
    .locals 1
    const/4 v0, 0x0  # false
    return v0
.end method
```

**方案2: 修改配置对象返回 null**
```smali
.method ... (...)L...UpdateConfig;
    .locals 1
    const/4 v0, 0x0
    return-object v0
.end method
```

**方案3: 修改版本比较跳转**
```smali
# 原始
if-lt vCurrent, vMin, :cond_force_update

# patch
goto :cond_no_update
```

---

### 假设3: 混淆 AlertDialog，文案动态生成 ⭐⭐⭐⭐
**可能性: 中高**

#### 根因分析
- 弹窗外观像系统 `AlertDialog`
- 搜索不到"立即更新" → 文案来自资源 ID / 动态拼接 / 加密字符串 / 远端配置
- 真正可定位特征: `setCancelable(false)` + `setCanceledOnTouchOutside(false)` + `show()` + `finish()` + `startActivity(ACTION_VIEW)`

#### 证据支持
- `strings /tmp/hg.apk | grep '立即更新'` 无输出
- `res/values*/strings.xml` 搜索也无输出
- 历史明确提到多个混淆类有 `setCancelable(false)`: `uc/e.java`, `od/b.java`, `com/tw.java`, `com/C6665qf.java`
- 用户描述"只能点击立即更新或强制关闭 APP" 吻合 `setCancelable(false)` + 拦截返回键

#### Patch 方案（兜底方案）

**不依赖类名，按字节码模式 patch**

```smali
# 原始 - 禁用取消
const/4 vA, 0x0
invoke-virtual {vD, vA}, Landroid/app/Dialog;->setCancelable(Z)V

# patch - 改为可取消
const/4 vA, 0x1
invoke-virtual {vD, vA}, Landroid/app/Dialog;->setCancelable(Z)V
```

```smali
# 原始 - 禁用外部点击关闭
const/4 vA, 0x0
invoke-virtual {vD, vA}, Landroid/app/Dialog;->setCanceledOnTouchOutside(Z)V

# patch - 改为可外部点击关闭
const/4 vA, 0x1
invoke-virtual {vD, vA}, Landroid/app/Dialog;->setCanceledOnTouchOutside(Z)V
```

**注意**: 这是兜底方案，不能彻底阻止弹窗，但能把"强制阻断"变成可关闭。更稳的做法仍是短路 `show()` 或更新判断。

---

### 假设4: 启动入口在 Application/SplashActivity ⭐⭐⭐
**可能性: 中**

#### 根因分析
- `MainFragmentActivity` 里的 URL 可能只是接口地址
- 真正调用链在启动生命周期:
  - `Application.onCreate()` 初始化更新 SDK
  - `SplashActivity.onCreate()` 入队弹窗
  - `MainActivity` 首次 `onResume` 展示
- 网络请求、配置解析、弹窗展示通常分散在不同类

#### 证据支持
- 弹窗启动即出现
- 历史分析中 `SplashActivity` 出现过 `AbsQueueDialog.show()`
- 当前 `hg-smali-patch.py` 只毒化 URL，不影响生命周期触发代码
- 使用 `--copy-original` 重打包时 Manifest 修改不生效 → "禁用 Activity" 类 patch 不可靠

#### 搜索建议
```bash
rg -n 'Application;->onCreate|SplashActivity|MainActivity|MainFragmentActivity|AbsQueueDialog;->show|checkUpdate|update' /tmp/apktool_out/smali*
```

#### Patch 方案
```smali
# 在启动入口找到更新检查调用
invoke-static {...}, Lx/y/z;->checkUpdate(...)V
invoke-virtual {...}, Lx/y/z;->showUpdateDialog(...)V

# patch
nop
```

```smali
# 如果调用返回对象，保留寄存器合法性
# 原始
invoke-static {...}, Lx/y/z;->getUpdateConfig(...)Lx/y/Config;
move-result-object v0

# patch
nop
const/4 v0, 0x0
```

---

### 假设5: 原始类名已重混淆，历史 patch 全部跑空 ⭐⭐⭐
**可能性: 中**

#### 根因分析
- 早期针对 `PopDefiner`, `UpgradePopupNewStyle`, `ForceUpdateInfo`, `PushImpl` 有效
- 当前"会员纯净修复版"可能重新混淆这些类
- 继续按原始类名 patch 会无命中或命中错误类

#### 证据支持
- 历史记录显示 v7 中这些 glob 均未命中，补丁基本跑空
- 真实命中转移到 `uc/e`, `od/b`, `com/tw`, `com/C6665qf` 等混淆类
- 当前脚本已退回到域名毒化 → 类名级 patch 不可靠

#### Patch 方案
放弃固定类名，改为 opcode 模式匹配（见假设3的兜底方案）

---

## 综合修复策略

### 推荐顺序

**第一优先级**（假设1 + 假设2 组合）:
1. 搜索 `setCancelable(false)` 定位实际弹窗类
2. 短路弹窗类的 `show()` 方法
3. 同时修改版本判断方法返回 false

**第二优先级**（假设4）:
1. 定位 `Application` / `SplashActivity` 启动入口
2. NOP 掉更新检查调用

**第三优先级**（兜底，假设3）:
1. 全局 patch `setCancelable(false)` → `setCancelable(true)`
2. 让弹窗可关闭（体验降级但可用）

### 验证命令

```bash
# 1. 反编译
apktool d hg.apk -o /tmp/apktool_out

# 2. 执行搜索（上述各假设的搜索命令）

# 3. 应用 patch

# 4. 重打包
apktool b /tmp/apktool_out -o hg-patched.apk

# 5. 签名
java -jar uber-apk-signer.jar --apks hg-patched.apk

# 6. 安装测试
adb install -r hg-patched-aligned-debugSigned.apk
```

---

## 下一步行动

1. ✅ **诊断完成** — 5 个假设已排序
2. ⏸️ **等待反编译产物** — 当前 `/tmp` 无 APK 反编译目录
3. 🔄 **待执行**: 下载最新红果 APK → 反编译 → 执行搜索命令 → 生成精确 patch 脚本
4. 🚀 **GHA 集成**: 将 patch 脚本集成到 `.github/workflows/hg-mod.yml`

---

## 相关文件

- **Patch 脚本**: `.github/scripts/hg-smali-patch.py`
- **Workflow**: `.github/workflows/hg-mod.yml`
- **历史分析工具**:
  - `hg-find-dialog.py`
  - `hg-find-update-string.py`
  - `hg-find-modder-update.py`
  - `hg-deep-analyze.py`
  - `hg-find-trigger.py`

---

**报告生成时间**: 2026-07-12 15:15 UTC+8  
**诊断耗时**: Codex 106 events (~3min), Antigravity 输出截断  
**可信度**: ⭐⭐⭐⭐ (基于历史实际命中 + 字节码模式分析)
