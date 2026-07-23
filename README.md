# BarkBridge v1.3.1

BarkBridge 是一款 Android 工具，可以把选定的微信通知和来电事件转发到 Bark。

BarkBridge is an Android utility that forwards selected WeChat notifications and incoming-call events to Bark.

## 功能 / Features

- 微信通知监听 / WeChat notification listener
- 微信消息详情推送 Bark / WeChat message detail forwarding to Bark
- 来电推送 Bark / Incoming-call forwarding to Bark
- 来电联系人名称匹配 / Contact-name lookup for incoming calls
- Bark Key 图形化配置 / Graphical Bark Key configuration
- 接收微信和来电推送总开关 / Master switch for WeChat and incoming-call forwarding
- 微信/来电独立开关 / Separate WeChat and incoming-call switches
- 短信通知、通用 App 通知、未接来电、电量状态转发 / SMS notification, generic app notification, missed-call, and battery-state forwarding
- 微信白名单远程回复入口 / Remote reply entry for whitelisted WeChat contacts
- Bark 回复链接和安卓轮询中转服务 / Bark reply links with Android-side relay polling
- Mac 微信远程回复模式 / Mac WeChat remote reply mode
- 勿扰时段和重要消息例外 / Quiet hours with important-message exceptions
- 自定义 Bark 服务器、分组、铃声、图标和通知级别 / Custom Bark server, group, sound, icon, and interruption level
- 配置导入导出 / Configuration import and export
- 配置自动保存 / Automatic configuration persistence
- 开机自启动接收器 / Boot startup receiver
- 后台常驻前台服务 / Foreground service
- 通知监听重绑辅助 / Notification listener rebind helper
- 息屏运行唤醒锁 / Wake lock for screen-off operation
- Bark 失败补发队列 / Delayed resend queue for failed Bark requests
- 失败补发手动管理 / Manual failed-resend management
- 微信关键词/联系人过滤 / WeChat keyword/contact filtering
- 可选屏蔽群聊消息 / Optional group-chat blocking
- 带时间戳的日志和隐私控制 / Timestamped logs with privacy controls
- 权限状态检测 / Permission status checks
- Material Design 3 风格原生界面 / Material Design 3 style native UI
- Telegram 讨论频道入口 / Telegram discussion channel entry
- 华为启动项手动管理快捷入口 / Huawei app launch manual-management shortcut
- 适配 Android 8 到 Android 15 / Android 8 to Android 15 target range
- GitHub Actions 自动构建 APK / GitHub Actions APK builds
- 支持本地属性或 GitHub Secrets 发布签名 / Optional release signing through local properties or GitHub Secrets

## 最新变化 / What's New

### v1.3.1

- 新增 Mac 微信远程回复模式：即使 Android 微信通知没有快捷回复按钮，也可以生成 Bark 回复链接。
- Mac 模式下 Android 只负责监听和生成链接，不再轮询消费回复队列。
- Cloudflare Worker 回复表单会保存联系人名，Mac 轮询后可以自动搜索联系人并发送回复。
- 新增 `tools/mac-wechat-relay.py`，用于 Mac 后台轮询中转服务并操作 Mac 微信发送。

- Added Mac WeChat remote reply mode: Bark reply links can be generated even when Android WeChat notifications do not expose quick reply.
- In Mac mode, Android only listens and creates reply links; it no longer consumes the reply queue.
- The Cloudflare Worker reply form now stores the contact name so the Mac relay can search and send through Mac WeChat.
- Added `tools/mac-wechat-relay.py` for polling the relay and sending replies through Mac WeChat.

### v1.3.0

- 新增微信远程回复第一档实现：优先使用 Android 通知快捷回复，不打开微信界面。
- Bark 微信推送可附带回复链接，iPhone 点开后可进入自建中转页面输入回复。
- Android 前台服务可轮询中转接口，收到 `{ "token": "...", "text": "..." }` 后调用微信通知快捷回复。
- 远程回复只对配置的联系人白名单生效；若远程回复联系人留空，则复用微信过滤白名单。
- 远程回复默认关闭，不影响现有微信、来电、短信、通用 App 和电量推送。

- Added first-stage WeChat remote reply using Android notification quick reply instead of opening WeChat.
- WeChat Bark pushes can include a reply link that opens a self-hosted relay page on iPhone.
- The Android foreground service can poll a relay endpoint and send `{ "token": "...", "text": "..." }` replies through WeChat quick reply.
- Remote reply only applies to configured contact allowlists; if its allowlist is empty, the WeChat forwarding allowlist is reused.
- Remote reply is disabled by default and does not affect existing forwarding features.

### v1.2.8

- 新增短信通知转发，优先通过默认短信 App/常见短信 App 的通知监听实现，不读取短信数据库。
- 新增通用 App 通知转发，可配置包名白名单。
- 新增未接来电提醒。
- 新增电量/充电状态提醒，包括充电连接、断开和低电量阈值。

- Added SMS notification forwarding through default/common SMS app notifications without reading the SMS database.
- Added generic app notification forwarding with a package-name whitelist.
- Added missed-call alerts.
- Added battery and charging-state alerts, including charging connected, disconnected, and low-battery threshold handling.

### v1.2.7

- 一次性新增 8 项增强：微信/来电独立开关、勿扰时段、推送内容格式优化、配置导入导出、首页运行状态、日志分类过滤、失败补发管理、华为设置引导区。
- 关闭某类接收后，该类消息不会推送，也不会进入补发队列。
- 配置导出会复制 JSON 到剪贴板；导入时把 JSON 粘贴回输入框即可。

- Added eight improvements in one release: separate WeChat/call switches, quiet hours, clearer push formatting, config import/export, top-level running status, categorized log filtering, resend management, and a Huawei settings guide.
- Disabled channels no longer send pushes or create pending resend items.
- Config export copies JSON to the clipboard; import by pasting the JSON back into the input box.

### v1.2.6

- 新增“接收微信和来电推送”总开关。
- 关闭后会忽略新的微信通知、来电事件和待补发队列，不再发送 Bark 推送。
- 测试 Bark 按钮仍可使用，方便单独检查 Bark Key 和网络。

- Added a master switch for WeChat and incoming-call forwarding.
- When disabled, BarkBridge ignores new WeChat notifications, incoming-call events, and pending resend flushes, so no Bark push is sent.
- The test Bark button remains available for checking the Bark Key and network separately.

### v1.2.5

- 修正华为应用启动管理跳转逻辑，避免跳到手机管家主屏幕。
- 优先尝试“应用和服务 - 应用启动管理”相关入口，失败时再回到 BarkBridge 应用详情页。

- Fixed the Huawei app launch-management shortcut so it no longer falls back to the Phone Manager home screen.
- The app now prioritizes entries related to "Apps and services - App launch management" and only falls back to BarkBridge app details if those entries fail.

### v1.2.4

- 优化主界面视觉层次，新增品牌顶部区域、圆角卡片、圆角输入框和更清晰的状态条。
- 日志区域改为浅色面板，权限状态使用不同颜色区分已开启和未开启。

- Refined the main UI with a branded header, rounded cards, rounded inputs, and clearer status rows.
- The log area now uses a soft panel, and permission states are color-coded for enabled and disabled states.

### v1.2.3

- 新增华为启动项管理快捷入口，位于权限检测区域。
- 该入口会尝试跳转到华为手机管家，方便把 BarkBridge 从“自动管理”改成“手动管理”。

- Added a Huawei startup-management shortcut in the permission section.
- The shortcut helps jump to Huawei Phone Manager so BarkBridge can be changed from automatic launch management to manual management.

### v1.2.2

- 新增“加入讨论”按钮，点击后打开 BarkBridge Telegram 讨论频道。

- Added a "加入讨论" button in the app that opens the BarkBridge Telegram discussion channel.

### v1.2

- 默认日志更清爽，屏幕、重绑、重复来电等排查记录只在诊断模式开启时显示。
- 可见日志增加时间戳，方便测试定位。
- 隐私控制支持隐藏手机号中间四位，也可以关闭微信消息正文日志保存。
- Bark 推送支持自定义服务器、分组、铃声、图标和通知级别。
- 微信转发规则支持屏蔽关键词、重要关键词、只允许联系人/关键词，以及可选屏蔽群聊。
- 主界面按 Bark 配置、权限、隐私、过滤、状态和最近记录重新整理。

- Quieter logs by default. Screen, rebind, duplicate-call, and other troubleshooting records are hidden unless diagnostic mode is enabled.
- Every visible log line includes a timestamp for easier testing.
- Privacy controls can mask phone numbers in logs and disable WeChat message-body logging.
- Bark delivery can be configured with a custom server, group, sound, icon, and interruption level.
- WeChat forwarding rules support blocked keywords, important keywords, allowed contacts/keywords, and optional group-chat blocking.
- The main screen is organized into clearer sections for Bark configuration, permissions, privacy, filters, status, and recent records.

## 当前 APK / Current APK

当前 APK 文件位于：

The current APK artifacts are included at:

```text
release/BarkBridge_v1.3.1-debug.apk
release/BarkBridge_v1.3.1-release-unsigned.apk
```

Debug APK 可直接用于测试安装。未签名 release APK 需要签名后再公开分发。

Debug APKs can be installed for testing. The unsigned release APK must be signed before public distribution.

注意：当前构建使用 Android 包名 `com.xueqijun.barkbridge`。较早的 v1.0 debug 构建使用 `com.example.barkbridge`，因此旧包会作为另一个 App 安装，不能原地覆盖升级。

Note: current builds use Android package `com.xueqijun.barkbridge`. Older v1.0 debug builds used `com.example.barkbridge`, so those older APKs install as a separate app instead of upgrading in place.

## 权限 / Permissions

BarkBridge 会请求以下权限：

BarkBridge requests these permissions:

- `INTERNET`
- `ACCESS_NETWORK_STATE`
- `READ_PHONE_STATE`
- `READ_CALL_LOG`
- `READ_PHONE_NUMBERS`
- `READ_CONTACTS`
- `POST_NOTIFICATIONS`
- `RECEIVE_BOOT_COMPLETED`
- `FOREGROUND_SERVICE`
- `FOREGROUND_SERVICE_DATA_SYNC`
- `REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`
- `WAKE_LOCK`

通知监听权限还需要在 Android 系统设置中手动开启。

Notification listener access must also be enabled manually in Android settings.

## 息屏推送 / Screen-Off Delivery

BarkBridge v1.3.1 的目标是在手机息屏或锁屏时继续转发微信通知、其他通知和来电事件。

BarkBridge v1.3.1 is designed to keep forwarding WeChat notifications, other notifications, and incoming-call events while the phone screen is off or locked.

App 使用前台服务、通知监听重绑、唤醒锁、后台联网状态检测和失败补发队列，让 Bark 推送在息屏期间尽量保持可用。

The app uses a foreground service, notification-listener rebinds, wake locks, background network status checks, and a resend queue so Bark pushes can continue during screen-off operation.

推荐设置：

Recommended settings:

- 开启 BarkBridge 通知监听权限。 / Enable BarkBridge notification listener access.
- 在 BarkBridge 中开启“接收微信和来电推送”。 / Enable "接收微信和来电推送" in BarkBridge.
- 允许 BarkBridge 忽略电池优化。 / Allow BarkBridge to ignore battery optimization.
- 在华为应用启动管理中，关闭 BarkBridge 的自动管理，然后手动开启自启动、关联启动和后台活动。 / In Huawei app launch management, turn off automatic management for BarkBridge, then manually enable auto-launch, secondary launch, and background activity.
- 允许 BarkBridge 使用 WLAN、移动数据和后台数据。 / Allow WLAN, mobile data, and background data for BarkBridge.
- 保持 BarkBridge 前台服务通知开启。 / Keep the BarkBridge foreground-service notification enabled.
- 仅在排查问题时开启 BarkBridge 诊断模式，日常使用可以关闭。 / In BarkBridge, enable diagnostic mode only when troubleshooting; normal use can keep it off.

如果临时网络失败，BarkBridge 会把失败的 Bark 推送加入队列，并在 App 恢复、设备解锁或前台服务重启时补发。

If a temporary network failure occurs, BarkBridge queues failed Bark pushes and resends them when the app is resumed, the device is unlocked, or the foreground service restarts.

## 远程回复 / Remote Reply

远程回复的执行端可以是 Android 手机上的微信 A，也可以是 Mac 上同时登录的微信 A。iPhone 上的微信 B 不能替微信 A 回复，只作为查看和输入回复内容的入口。

Remote replies can be executed by WeChat A on the Android phone or by the same WeChat A logged in on Mac. WeChat B on iPhone cannot reply on behalf of WeChat A; it only acts as the viewing and input entry.

实现链路：

Flow:

- Android 监听微信 A 通知，并匹配联系人白名单。
- Mac 模式下，BarkBridge 不要求 Android 微信通知带快捷回复按钮，也会生成短期有效 token。
- Android 模式下，只有微信通知包含快捷回复动作时才会生成 token。
- Bark 推送到 iPhone，并通过 Bark 的 `url` 参数附带回复页面链接。
- iPhone 打开回复页面并提交回复内容到你的中转服务。
- Mac 模式下，Mac 脚本轮询中转接口，拿到 contact 和 text 后操作 Mac 微信发送。
- Android 模式下，Android 前台服务轮询中转接口，拿到 token 和 text 后调用微信通知快捷回复。

- Android listens to WeChat A notifications and matches the contact allowlist.
- In Mac mode, BarkBridge creates a short-lived token even if the Android WeChat notification does not expose quick reply.
- In Android mode, a token is created only when the WeChat notification contains a quick-reply action.
- Bark pushes to iPhone and includes the reply page through Bark's `url` parameter.
- iPhone opens the reply page and submits the reply text to your relay service.
- In Mac mode, the Mac relay script polls the relay endpoint, receives contact and text, then sends through Mac WeChat.
- In Android mode, the Android foreground service polls the relay endpoint, receives token and text, then sends through WeChat quick reply.

中转接口返回格式可以是单条对象、数组，或包含 `replies` 数组的对象：

The relay polling endpoint may return one object, an array, or an object with a `replies` array:

```json
{"id":"reply-001","token":"token-from-bark-link","text":"收到，我稍后处理"}
```

```json
[{"id":"reply-001","token":"token-from-bark-link","text":"收到，我稍后处理"}]
```

```json
{"replies":[{"id":"reply-001","token":"token-from-bark-link","text":"收到，我稍后处理"}]}
```

仓库内提供了一个 Cloudflare Worker 示例：`relay/cloudflare-worker.js`。部署时绑定一个 KV 命名空间到 `REPLIES`，可选设置环境变量 `REPLY_SECRET`。App 中这样配置：

A Cloudflare Worker sample is included at `relay/cloudflare-worker.js`. Bind a KV namespace as `REPLIES`, and optionally set `REPLY_SECRET`. Configure the app like this:

```text
iPhone 回复页面 URL: https://your-worker.example.workers.dev/reply
轮询取回复 URL: https://your-worker.example.workers.dev/poll?secret=your-secret
```

Mac 微信远程回复：

Mac WeChat remote reply:

```sh
python3 tools/mac-wechat-relay.py \
  --poll-url 'https://your-worker.example.workers.dev/poll?secret=your-secret' \
  --interval 5
```

首次运行时，macOS 通常会要求给运行脚本的 App 授予“辅助功能”权限。路径：

On first run, macOS usually requires Accessibility permission for the app running the script:

```text
系统设置 -> 隐私与安全性 -> 辅助功能
System Settings -> Privacy & Security -> Accessibility
```

如果要后台常驻，可以参考 `tools/com.xueqijun.barkbridge.mac-relay.plist.example` 配置 launchd。

For background operation, use `tools/com.xueqijun.barkbridge.mac-relay.plist.example` as a launchd template.

限制：

Limitations:

- Android 快捷回复模式依赖微信通知是否提供快捷回复动作。
- Mac 模式不依赖 Android 通知快捷回复，但 Mac 必须开机、微信必须登录，且不能处于无法执行 UI 自动化的锁屏状态。
- Android 快捷回复模式要求原通知仍在、token 未过期时才能回复；当前 token 有效期约 30 分钟。
- Mac 模式依赖 Mac 微信搜索联系人和粘贴发送，微信界面变化可能影响自动化。

- Android quick-reply mode depends on whether WeChat exposes a quick-reply action in its notification.
- Mac mode does not depend on Android quick reply, but the Mac must be on, WeChat must be logged in, and the Mac must not be in a locked state that prevents UI automation.
- Android quick-reply mode requires the original notification to remain valid and the token to stay unexpired; current token lifetime is about 30 minutes.
- Mac mode depends on Mac WeChat contact search and paste/send automation, so WeChat UI changes may affect it.

## 构建 / Build

这是一个 Gradle Android 项目：

This project is a Gradle Android application:

```sh
./gradlew assembleDebug
```

也支持 release 构建：

Release builds are also supported:

```sh
./gradlew assembleRelease
```

未配置签名信息时，Gradle 会生成未签名 release APK。

Without signing configuration, Gradle produces an unsigned release APK.

## 发布签名 / Release Signing

本地 release 签名可在 `local.properties` 中配置：

For local release signing, create `local.properties` with:

```properties
BARKBRIDGE_STORE_FILE=/absolute/path/to/barkbridge-release.jks
BARKBRIDGE_STORE_PASSWORD=your_store_password
BARKBRIDGE_KEY_ALIAS=your_key_alias
BARKBRIDGE_KEY_PASSWORD=your_key_password
```

GitHub Actions 签名 release 构建需要配置以下仓库 Secrets：

For GitHub Actions signed release builds, configure these repository secrets:

- `BARKBRIDGE_KEYSTORE_BASE64`
- `BARKBRIDGE_STORE_PASSWORD`
- `BARKBRIDGE_KEY_ALIAS`
- `BARKBRIDGE_KEY_PASSWORD`

生成 `BARKBRIDGE_KEYSTORE_BASE64`：

Generate `BARKBRIDGE_KEYSTORE_BASE64` with:

```sh
base64 -i barkbridge-release.jks
```

## GitHub Releases

推送类似 `v1.3.1` 的 tag 后，GitHub Actions 会自动构建 APK 并发布到 GitHub Release 页面。

Pushing a tag such as `v1.3.1` builds APKs and publishes them to the GitHub Release page automatically.
