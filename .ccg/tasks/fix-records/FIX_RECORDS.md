# 红果短剧修改 — 修正记录 / Fix Records

> 记录所有尝试过的修改、结果、教训。避免重复踩坑。

## 修改记录

### 2026-07-19 — gethostbyname → NULL（当前方案）
- **方案**: patch `libseccore.so` 的 gethostbyname PLT → 返回 NULL（host not found）
- **socket()** 不碰（之前导致 SIGSEGV）
- **network_security_config** 域名封锁保留
- **trust-anchors** 保留（拦 Java HTTP/HTTPS）
- **CJPaySDK**: 不删文件（JNI 引用会崩），只 NOP 调用
- **状态**: ⏳ 测试中

### 2026-07-18 — socket() PLT patch → SIGSEGV ❌
- **方案**: patch `libseccore.so` 的 socket() → 返回 -1
- **结果**: SIGSEGV（so 把 -1 当文件描述符直接用）
- **教训**: 不能 patch 返回值类型为 int 且返回后直接使用的函数

### 2026-07-18 — CJPaySDK 文件删除 → SIGSEGV ❌
- **方案**: 删除 `com/android/ttcjpaysdk` 全部 1684 个 smali 文件
- **结果**: SIGSEGV（`libseccore.so` 通过 JNI 持有对已删除类的引用 → 野指针）
- **教训**: 字节跳动 APP 用自定义 classloader（NewMiraClassloader），native 层有 JNI 引用缓存。删文件会让这些引用变成悬空指针。

### 2026-07-18 — trust-anchors 空锚点 → 卡闪屏 ✅/❌ 部分有效
- **方案**: `network_security_config` 加 `<trust-anchors></trust-anchors>` → SSL 握手失败
- **结果**: 鹿属声明弹窗 ✅ 消失，但卡住了一个更新弹窗（native 层绕过）
- **教训**: trust-anchors 对 Java 层 OKHttp/HttpURLConnection 有效，对 native 层 JNI 调绕过

### 2026-07-18 — pin-set 无效 SHA-256 → XML 解析失败 ❌
- **方案**: pin-set 加伪 SHA-256 hash
- **结果**: 整个 `network_security_config.xml` 解析失败 → 回退默认（放行全部）
- **教训**: Android 对 pin-set 的 base64 格式有严格校验，伪 hash 导致整段 XML 失效

### 2026-07-18 — cleartextTrafficPermitted="false" → 不拦 HTTPS ❌
- **方案**: `cleartextTrafficPermitted="false"` 只拦 HTTP 明文
- **结果**: HTTPS 请求不受影响，弹窗依然显示
- **教训**: 只用 cleartext 不够，必须配合 trust-anchors

### 2026-07-18 — 删 SafeLoader/checkerframework smali → 崩溃 ❌
- **方案**: 删除 `sgcore0` 和 `org/checkerframework/.../security` 目录
- **结果**: `<clinit>` 中 `SafeLoader.registerNativesForClass()` 找不到类 → 崩溃
- **教训**: `libseccore.so` 在 `JNI_OnLoad` 时注册所有 native 方法，注册失败直接崩

### 2026-07-17 — UPDATE_VERSION_CODE = MAX_INT → 影响版本追踪 ❌
- **方案**: AndroidManifest 中 UPDATE_VERSION_CODE 改成 2147483647
- **结果**: 更新弹窗消失，但影响版本追踪（用户说不行）
- **教训**: 改版本号是下策

### 2026-07-15 — 域名清空 + NOP checkUpdate（第一次成功） ✅
- **方案**: plan-b 清空 oneseeker.top 字符串 + smali-patch 域名打毒 + checkUpdate NOP
- **结果**: 两个更新弹窗都消失了（当时用的官方 CDN 版，有旧 SDK）
- **教训**: 最简单的方案往往最稳。不删文件、不打 so、不加 trust-anchors
