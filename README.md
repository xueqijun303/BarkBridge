# BarkBridge v1.2.3

BarkBridge 是一款 Android 工具，可以把选定的微信通知和来电事件转发到 Bark。

BarkBridge is an Android utility that forwards selected WeChat notifications and incoming-call events to Bark.

## 功能 / Features

- 微信通知监听 / WeChat notification listener
- 微信消息详情推送 Bark / WeChat message detail forwarding to Bark
- 来电推送 Bark / Incoming-call forwarding to Bark
- 来电联系人名称匹配 / Contact-name lookup for incoming calls
- Bark Key 图形化配置 / Graphical Bark Key configuration
- 自定义 Bark 服务器、分组、铃声、图标和通知级别 / Custom Bark server, group, sound, icon, and interruption level
- 配置自动保存 / Automatic configuration persistence
- 开机自启动接收器 / Boot startup receiver
- 后台常驻前台服务 / Foreground service
- 通知监听重绑辅助 / Notification listener rebind helper
- 息屏运行唤醒锁 / Wake lock for screen-off operation
- Bark 失败补发队列 / Delayed resend queue for failed Bark requests
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
release/BarkBridge_v1.2.3-debug.apk
release/BarkBridge_v1.2.3-release-unsigned.apk
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

BarkBridge v1.2.3 的目标是在手机息屏或锁屏时继续转发微信通知和来电事件。

BarkBridge v1.2.3 is designed to keep forwarding WeChat notifications and incoming-call events while the phone screen is off or locked.

App 使用前台服务、通知监听重绑、唤醒锁、后台联网状态检测和失败补发队列，让 Bark 推送在息屏期间尽量保持可用。

The app uses a foreground service, notification-listener rebinds, wake locks, background network status checks, and a resend queue so Bark pushes can continue during screen-off operation.

推荐设置：

Recommended settings:

- 开启 BarkBridge 通知监听权限。 / Enable BarkBridge notification listener access.
- 允许 BarkBridge 忽略电池优化。 / Allow BarkBridge to ignore battery optimization.
- 在华为应用启动管理中，关闭 BarkBridge 的自动管理，然后手动开启自启动、关联启动和后台活动。 / In Huawei app launch management, turn off automatic management for BarkBridge, then manually enable auto-launch, secondary launch, and background activity.
- 允许 BarkBridge 使用 WLAN、移动数据和后台数据。 / Allow WLAN, mobile data, and background data for BarkBridge.
- 保持 BarkBridge 前台服务通知开启。 / Keep the BarkBridge foreground-service notification enabled.
- 仅在排查问题时开启 BarkBridge 诊断模式，日常使用可以关闭。 / In BarkBridge, enable diagnostic mode only when troubleshooting; normal use can keep it off.

如果临时网络失败，BarkBridge 会把失败的 Bark 推送加入队列，并在 App 恢复、设备解锁或前台服务重启时补发。

If a temporary network failure occurs, BarkBridge queues failed Bark pushes and resends them when the app is resumed, the device is unlocked, or the foreground service restarts.

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

推送类似 `v1.2.3` 的 tag 后，GitHub Actions 会自动构建 APK 并发布到 GitHub Release 页面。

Pushing a tag such as `v1.2.3` builds APKs and publishes them to the GitHub Release page automatically.
