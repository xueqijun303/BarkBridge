# BarkBridge v1.3.14

BarkBridge 是一款 Android 工具，可以把选定的微信通知和来电事件转发到 Bark。

BarkBridge is an Android utility that forwards selected WeChat notifications and incoming-call events to Bark.

## 当前状态 / Current Status

- 当前稳定版本：`v1.3.14`。
- Android 端已切换到阿里云自托管中继，默认地址为 `http://47.101.153.215:8787`。
- iPhone 端统一使用 `/chat` 聊天/回复页面查看完整消息、选择联系人和提交回复。
- Mac 端通过轮询中继服务接收回复指令，并使用 Mac 微信客户端代发。
- 自托管中继已验证 `/chat`、`/admin`、`/settings`、`/control`、`/api/status` 和 `/health` 可用。

- Current stable version: `v1.3.14`.
- Android now uses the Aliyun self-hosted relay by default at `http://47.101.153.215:8787`.
- iPhone uses the unified `/chat` page to view full messages, choose contacts, and submit replies.
- Mac polls the relay service for reply commands and sends them through Mac WeChat.
- The self-hosted relay has verified `/chat`, `/admin`, `/settings`, `/control`, `/api/status`, and `/health`.

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
- 微信语音消息 Mac 转文字实验模式 / Experimental Mac WeChat voice-to-text mode
- 统一聊天/回复页面 / Unified chat and reply page
- 完整消息聊天面板 / Full-message chat panel
- 聊天联系人搜索、置顶、隐藏 / Chat contact search, pinning, and hiding
- 单联系人聊天记录清空 / Per-contact chat-history clearing
- 每联系人最近 100 条自动保留 / Automatic per-contact retention for the latest 100 messages
- 中继状态面板和健康检查 / Relay status dashboard and health check
- 自托管管理页和 Mac 状态回传 / Self-hosted admin page and Mac status reporting
- 语音转文字失败截图诊断 / Voice-to-text failure screenshot diagnostics
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

### 当前开发进展 / Current Development

- 自托管中继新增任务状态表和 `/api/tasks`、`/api/task/status` 接口，用于记录每条回复/语音任务的 `queued`、`claimed`、`processing`、`sending`、`sent`、`retry`、`failed` 等状态。
- Mac relay 会在领取任务、打开联系人、发送成功、人工确认、失败重试和最终失败时回写状态，中继管理页可看到完整处理链路。
- iPhone 聊天面板中的发出消息会随 Mac relay 回写同步更新状态，不再只停留在 `queued`。
- 语音转文字任务进入独立队列管理，每条语音任务都有单独状态、重试次数和失败原因，降低连续语音遗漏风险。
- 为避免重复发送，失败重试仍优先使用 Mac 本地 pending 队列，服务端负责可观测状态而不重复派发同一任务。

- The self-hosted relay now has a task-status table plus `/api/tasks` and `/api/task/status` endpoints for per-task states such as `queued`, `claimed`, `processing`, `sending`, `sent`, `retry`, and `failed`.
- Mac relay reports state transitions when it claims a task, opens a contact, sends successfully, falls back to manual review, retries, or finally fails.
- Outgoing messages in the iPhone chat panel now receive Mac relay status updates instead of staying at `queued`.
- Voice-to-text tasks are tracked individually with status, retry count, and failure reason, reducing missed consecutive voice-message transcriptions.
- To avoid duplicate sends, failed retries still use the Mac local pending queue first, while the relay records observability state instead of dispatching the same task twice.

### v1.3.13

- 新增自托管中继管理页 `/admin?secret=...`，集中显示中继、Android 上传、Mac 轮询、Mac 状态回传、待处理队列和最近错误。
- Mac relay 会向自托管中继回传运行状态，包括轮询模式、进程号、语音转文字开关、待处理队列、最近发送、最近识别标题和最近错误。
- 微信语音转文字失败时，Mac relay 会在 `~/.barkbridge/voice-debug/` 保存聊天区域截图和 OCR 框 JSON，方便定位点击或识别问题。
- 聊天、控制和设置页面增加管理页入口。

- Added the self-hosted admin page `/admin?secret=...` for relay, Android upload, Mac polling, Mac status reporting, pending queue, and latest error visibility.
- Mac relay now reports runtime status back to the self-hosted relay, including poll mode, process id, voice-to-text switch, pending queue, last send, last recognized title, and latest error.
- When WeChat voice-to-text fails, Mac relay saves a chat-area screenshot and OCR-box JSON under `~/.barkbridge/voice-debug/` for diagnosis.
- Added admin links to the chat, control, and settings pages.

### Mac relay update

- 微信语音转文字仍标记为实验功能，并且 Mac relay 默认不启用自动点击：Mac 微信聊天区不暴露可用无障碍控件，本地消息数据库也不是明文 SQLite，因此当前 UI/OCR 方案可能受窗口布局、气泡长度和微信版本影响。
- Mac relay 新增语音任务过期和独立重试控制，失败语音任务不会长期卡住后续文字收发。
- 新增 `tools/mac-wechat-voice-inspector.py`，用于观察新语音消息在 Mac 微信本地数据目录触发了哪些文件变化，为后续改成音频文件级转写做准备。

- WeChat voice-to-text remains experimental and Mac relay does not enable automatic UI clicking by default: the current Mac WeChat chat view does not expose usable Accessibility elements, and the local message databases are not plain SQLite, so the UI/OCR approach can be affected by window layout, bubble length, and WeChat versions.
- Mac relay now applies voice-task TTL and a separate retry limit so failed voice tasks do not block normal text forwarding.
- Added `tools/mac-wechat-voice-inspector.py` to observe file changes caused by new Mac WeChat voice messages, which helps evaluate a future audio-file-based transcription path.

### v1.3.12

- 聊天面板上传失败时，Android 日志会显示服务器返回的错误内容，方便区分 403 密钥错误和其他网络问题。
- Android 自动复用 relay secret 的范围扩大到“iPhone 聊天面板 URL”和“聊天记录上传 URL”。
- 自托管中继 `/ingest` 支持从 URL query 读取 `secret`，降低配置错误概率。

- Android now logs the relay error body when chat-panel upload fails, making 403 secret errors easier to diagnose.
- Android can now reuse the relay secret from the iPhone chat page URL or conversation ingest URL.
- The self-hosted relay `/ingest` endpoint can also read `secret` from the URL query string.

### v1.3.11

- 修正 Mac 微信语音转文字实验功能的点击策略：优先点击聊天窗口中可见的“转文字”按钮，并等待实际转写结果。
- 避免连续点击多个候选点导致误选消息或混入 OCR 噪声。

- Fixed the experimental Mac WeChat voice-to-text click strategy: the relay now prioritizes the visible "转文字" button and waits for the actual transcription result.
- Avoids clicking multiple candidate points in a row, which could select messages or mix UI noise into OCR output.

### v1.3.10

- Android 端识别微信语音通知，并在聊天面板中记录“等待 Mac 微信转文字”的占位消息。
- 新增“微信语音消息请求 Mac 转文字”开关，可随时关闭实验功能。
- 自托管中继收到语音转文字请求后，会把 `voice_transcribe` 任务放入 Mac relay 轮询队列。
- Mac relay 新增实验性语音转文字处理：打开对应微信会话，尝试调用 Mac 微信的“转文字/转换为文字”菜单，并把转出的文字回写到聊天面板。
- Mac relay 支持 `--ingest-url`，默认可从 `--poll-url` 自动推导 `/ingest` 回写地址。

- Android now detects WeChat voice notifications and records a pending voice-to-text placeholder in the chat panel.
- Added a "微信语音消息请求 Mac 转文字" toggle so the experimental feature can be disabled at any time.
- The self-hosted relay now queues a `voice_transcribe` task for Mac relay when it receives a voice transcription request.
- Mac relay adds experimental voice-to-text handling by opening the matching WeChat conversation, trying WeChat's built-in voice-to-text menu, and writing the result back to the chat panel.
- Mac relay supports `--ingest-url`; by default it derives `/ingest` from `--poll-url`.

### v1.3.9

- Android Bark 通知统一跳转到 `/chat?secret=...&contact=...`，同一个页面即可查看上下文并提交回复。
- 自托管中继聊天页新增联系人搜索、置顶/隐藏配置、`回到最新` 和 `清空当前联系人记录`。
- 自托管中继新增 `/settings`、`/api/status` 和 `/health`，方便从手机管理联系人显示并查看 Android/Mac/队列状态。
- 聊天记录改为每个联系人自动保留最近 100 条，全局最多保留 5000 条，避免长期使用后数据库过大。
- Mac relay 发送失败回执增加目标、重试次数、失败原因和手动确认状态，发送排查更清楚。
- 自托管安装脚本支持升级时停止旧服务和旧进程，避免 8787 端口被旧 relay 占用导致部署没生效。
- GitHub Actions APK 产物名改为跟随当前 tag/版本自动生成。

- Android Bark pushes now open `/chat?secret=...&contact=...`, so the same page can show context and submit replies.
- The self-hosted chat page now includes contact search, pinned/hidden contact settings, "Back to latest", and per-contact history clearing.
- The self-hosted relay adds `/settings`, `/api/status`, and `/health` for contact-display management and Android/Mac/queue status checks.
- Chat history now keeps the latest 100 messages per contact and up to 5000 messages globally to keep the database bounded.
- Mac relay failure receipts now include the target, retry count, failure reason, and manual-review state.
- The self-hosted installer now stops old services/processes during upgrades so port 8787 is not left serving stale relay code.
- GitHub Actions APK artifact names now follow the current tag/version automatically.

### v1.3.8

- Android 网络安全配置允许访问阿里云自托管中继 `http://47.101.153.215:8787`，修复 `Cleartext HTTP traffic ... not permitted` 导致的聊天记录上传失败。

- Android network security config now allows the Aliyun self-hosted relay at `http://47.101.153.215:8787`, fixing conversation upload failures caused by `Cleartext HTTP traffic ... not permitted`.

### v1.3.7

- 聊天面板上传结果会写入普通日志，不再依赖诊断模式，方便确认 Android 手机是否真的把收到的微信通知上传到 Worker。
- 远程回复配置区新增“测试聊天面板上传”按钮，可从 Android 手机直接写入一条 `BarkBridge手机自测` 消息到聊天面板。
- 新增自托管中继服务 `relay/self-hosted-relay.py`，可部署到自己的服务器，绕开 `workers.dev` 网络不稳定问题。
- 默认中继地址已切换到阿里云自托管服务 `http://47.101.153.215:8787`。

- Conversation-mirror upload results are now written to normal logs instead of diagnostic-only logs, making it easier to verify whether Android really uploads captured WeChat notifications to the Worker.
- Added a "测试聊天面板上传" button in the remote-reply settings section; it writes a `BarkBridge手机自测` message from Android into the chat panel.
- Added `relay/self-hosted-relay.py` for deploying the relay on your own server when `workers.dev` is unstable or blocked.
- The default relay base URL now points to the Aliyun self-hosted service at `http://47.101.153.215:8787`.

### v1.3.6

- 新增聊天面板：`/chat?secret=...` 可以在 iPhone 浏览器查看 BarkBridge 捕获到的完整微信通知正文和已提交的回复。
- Android 端新增“聊天面板完整消息记录”配置，微信通知会额外上传到 Worker 的 `/ingest`，不依赖 Bark 通知预览长度。
- Bark 微信通知现在优先跳转到完整会话页，通知正文中仍保留直接回复链接。
- 聊天面板只记录 BarkBridge 启用后捕获和发送过的内容，不读取微信数据库，也不会导入历史聊天记录。

- Added a chat panel at `/chat?secret=...` for viewing full WeChat notification text and submitted replies from iPhone.
- Android now has a conversation-mirror setting that uploads WeChat notifications to the Worker's `/ingest` endpoint, independent of Bark notification preview length.
- WeChat Bark pushes now open the full conversation page first, while still keeping the direct reply link in the push body.
- The chat panel only records messages captured or sent after BarkBridge is enabled; it does not read the WeChat database or import old chat history.

### v1.3.5

- Mac 本地控制台升级为运维面板：显示轮询模式、最近轮询、待发队列、最近发送、OCR 识别标题和最近错误。
- 新增 Mac relay 控制开关：暂停、允许自动发送、仅手动模式。
- 新增联系人规则网页编辑：目标联系人、别名、自动发送、标题校验和备注。
- 新增发送审计记录视图，并在连续失败 3 次后自动暂停对应联系人的自动发送。
- Cloudflare Worker 新增 `/control?secret=...` 远程控制页，可从 iPhone 暂停/恢复 Mac relay、开关自动发送和仅手动模式。

- The Mac local console is now an operations dashboard showing poll mode, last poll, pending queue, last send, OCR-recognized title, and latest error.
- Added Mac relay controls: pause, auto-send master switch, and manual-only mode.
- Added web editing for contact rules: target, aliases, auto-send, title verification, and notes.
- Added an audit-log view, and auto-pauses a contact's auto-send after 3 consecutive failures.
- The Cloudflare Worker now provides `/control?secret=...` for iPhone-side remote control of pause/resume, auto-send, and manual-only mode.

### v1.3.4

- Mac 微信自动发送前会通过本机 OCR 识别当前会话标题，只有识别结果匹配目标联系人/群聊时才会发送。
- 如果目标校验失败，Mac relay 会拦截发送、复制人工确认内容，并通过 Bark 回执报告实际识别到的会话。
- Cloudflare Worker 轮询支持 `waitMs` 参数；Mac relay 会自动探测线上 Worker 是否支持该参数，未部署新版 Worker 时自动使用兼容长轮询。
- iPhone 回复/主动发送页面改为移动端优先布局，联系人列表改为纵向选择，正文和输入框字体放大。

- Before sending through Mac WeChat, the Mac relay now reads the current chat title with local OCR and sends only when it matches the target contact or group.
- If target verification fails, the relay blocks the send, copies a manual-review payload, and reports the recognized chat through a Bark receipt.
- Cloudflare Worker polling supports a `waitMs` parameter; the Mac relay auto-detects support and falls back to legacy long polling until the updated Worker is deployed.
- The iPhone reply/compose page now uses a mobile-first layout with a vertical contact list and larger message/input text.

### v1.3.3

- Mac 远程回复默认开启，并内置当前 Cloudflare Worker 回复页地址。
- Bark 推送正文中直接显示完整回复 URL，同时仍设置 Bark 的 `url` 跳转参数。
- 这样即使 Bark 客户端不明显展示跳转按钮，也能从通知正文看到并打开回复链接。

- Mac remote reply is enabled by default and uses the current Cloudflare Worker reply page by default.
- Bark push bodies now include the full reply URL while still setting Bark's `url` parameter.
- This makes the reply link visible even when the Bark client does not clearly show the URL action.

### v1.3.2

- 修正 Mac 微信远程回复模式生成链接过于严格的问题。
- Mac 模式下，“Mac 回复白名单”留空时，所有已正常推送到 Bark 的微信消息都会附带回复链接。
- 如果缺少回复页面 URL 或联系人未命中白名单，App 会在“回复”日志里明确记录原因。

- Fixed overly strict reply-link generation in Mac WeChat remote reply mode.
- In Mac mode, when the Mac reply allowlist is empty, every WeChat message already forwarded to Bark gets a reply link.
- If the reply page URL is missing or a contact does not match the allowlist, the app logs the reason under the reply category.

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

## APK / APK Artifacts

GitHub Actions 会生成以下 APK 产物名：

GitHub Actions produces APK artifacts with these names:

```text
BarkBridge_v1.3.13-debug.apk
BarkBridge_v1.3.13-release.apk
BarkBridge_v1.3.13-release-unsigned.apk
```

Debug APK 可直接用于测试安装。未签名 release APK 需要签名后再公开分发；如果配置了签名 Secrets，Actions 会生成已签名 release APK。

Debug APKs can be installed for testing. The unsigned release APK must be signed before public distribution; when signing secrets are configured, Actions produces a signed release APK.

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

BarkBridge v1.3.13 的目标是在手机息屏或锁屏时继续转发微信通知、其他通知和来电事件。

BarkBridge v1.3.13 is designed to keep forwarding WeChat notifications, other notifications, and incoming-call events while the phone screen is off or locked.

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
- Bark 推送到 iPhone，并通过 Bark 的 `url` 参数打开统一聊天/回复页面。
- iPhone 打开统一聊天/回复页面并提交回复内容到你的中转服务。
- Mac 模式下，Mac 脚本轮询中转接口，拿到 contact 和 text 后操作 Mac 微信发送。
- Android 模式下，Android 前台服务轮询中转接口，拿到 token 和 text 后调用微信通知快捷回复。

- Android listens to WeChat A notifications and matches the contact allowlist.
- In Mac mode, BarkBridge creates a short-lived token even if the Android WeChat notification does not expose quick reply.
- In Android mode, a token is created only when the WeChat notification contains a quick-reply action.
- Bark pushes to iPhone and opens the unified chat/reply page through Bark's `url` parameter.
- iPhone opens the unified chat/reply page and submits the reply text to your relay service.
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

当前推荐使用自托管中继的统一聊天页。仓库内仍保留 Cloudflare Worker 示例：`relay/cloudflare-worker.js`，适合不使用阿里云自托管时部署。部署 Worker 时绑定 Durable Object：`RELAY` -> `RelayRoom`，可选设置环境变量 `REPLY_SECRET`。

The recommended setup now uses the self-hosted relay's unified chat page. A Cloudflare Worker sample is still included at `relay/cloudflare-worker.js` for non-self-hosted deployments. Bind a Durable Object as `RELAY` -> `RelayRoom`, and optionally set `REPLY_SECRET`.

推荐配置：

Recommended configuration:

```text
iPhone 聊天面板 URL: http://47.101.153.215:8787/chat
轮询取回复 URL: http://47.101.153.215:8787/poll?secret=your-secret
```

Cloudflare Worker 备选配置：

Cloudflare Worker alternative:

```text
iPhone 回复页面 URL: https://your-worker.example.workers.dev/reply
轮询取回复 URL: https://your-worker.example.workers.dev/poll?secret=your-secret
```

新版 Worker 支持 `waitMs` 查询参数，例如 `/poll?secret=your-secret&waitMs=8000`。Mac relay 会自动探测该能力；如果线上 Worker 还没部署新版，它会继续使用 25 秒兼容长轮询，避免回复被发给已断开的请求。

The updated Worker supports a `waitMs` query parameter, for example `/poll?secret=your-secret&waitMs=8000`. The Mac relay detects this automatically. If the deployed Worker has not been updated yet, it keeps using 25-second legacy long polling to avoid losing replies to a disconnected request.

Mac 模式下，如果“Mac 回复白名单”留空，所有已正常推送到 Bark 的微信通知都会带回复链接。需要限制联系人时，再填写微信通知标题里显示的联系人名。

In Mac mode, if the Mac reply allowlist is empty, every WeChat notification already forwarded to Bark includes a reply link. Fill it only when you want to restrict reply-enabled contacts.

## 聊天面板 / Chat Panel

聊天面板用于解决 Bark 通知预览显示不全的问题。Android 捕获到微信通知后，会把完整通知正文上传到中继服务的 `/ingest`，iPhone 打开 `/chat?secret=...&contact=...` 后可以按联系人查看完整往来内容，并从同一页面提交回复。

The chat panel is designed for cases where Bark's notification preview truncates long text. When Android captures a WeChat notification, it uploads the full notification body to the relay's `/ingest` endpoint. Open `/chat?secret=...&contact=...` on iPhone to view full conversations by contact and submit replies from the same page.

聊天页支持：

The chat page supports:

- 联系人搜索、置顶和隐藏。 / Contact search, pinning, and hiding.
- `回到最新`，用于长对话快速回到底部最新消息。 / `Back to latest` for jumping to the newest message in long conversations.
- `清空当前联系人记录`，只清除当前联系人的云端聊天记录。 / Per-contact clearing that deletes only the selected contact's cloud-side chat history.
- 每个联系人自动保留最近 100 条记录，全局最多保留 5000 条。 / Automatic retention of the latest 100 messages per contact and up to 5000 messages globally.

App 中可配置：

Configure these fields in the app:

```text
聊天记录上传 URL: http://47.101.153.215:8787/ingest
iPhone 聊天面板 URL: http://47.101.153.215:8787/chat
聊天面板密钥 secret: your-secret
```

如果“聊天面板密钥 secret”留空，BarkBridge 会尝试从远程回复页面 URL 或轮询 URL 的 `secret` 参数中复用密钥。

If the chat-panel secret is left empty, BarkBridge tries to reuse the `secret` query parameter from the remote reply page URL or poll URL.

限制：聊天面板只保存 BarkBridge 启用后捕获到的通知正文和通过中转服务提交的回复；它不读取微信数据库，因此不会显示历史聊天记录，也不能补全微信没有放进通知里的内容。清空记录只影响 BarkBridge 中继数据库，不会删除微信里的原始聊天。

Limitation: the chat panel only stores notification text captured after BarkBridge is enabled and replies submitted through the relay. It does not read the WeChat database, so it cannot import old chat history or recover content that WeChat did not include in the notification. Clearing history only affects the BarkBridge relay database; it does not delete the original WeChat conversation.

## 自托管中继 / Self-Hosted Relay

如果 Android 手机直连 `workers.dev` 不稳定，可以把中继服务部署到自己的服务器。自托管版本提供 `/ingest`、`/chat`、`/admin`、`/settings`、`/send`、`/poll`、`/control`、`/api/status` 和 `/health` 等路径，Android 和 Mac 只需要替换域名/IP。

If Android cannot reliably reach `workers.dev`, deploy the relay on your own server. The self-hosted version provides paths such as `/ingest`, `/chat`, `/admin`, `/settings`, `/send`, `/poll`, `/control`, `/api/status`, and `/health`, so Android and Mac only need a URL change.

默认部署端口是 `8787`，不会占用常见的 `80`、`443` 或 `8001`：

The default port is `8787`, so it does not take over common ports like `80`, `443`, or `8001`:

```sh
sudo BARKBRIDGE_RELAY_SECRET='your-secret' bash relay/install-self-hosted.sh
```

部署后配置：

Configure after deployment:

```text
聊天记录上传 URL: http://47.101.153.215:8787/ingest
iPhone 聊天面板 URL: http://47.101.153.215:8787/chat
聊天面板密钥 secret: your-secret
轮询取回复 URL: http://47.101.153.215:8787/poll?secret=your-secret
```

常用页面：

Useful pages:

```text
聊天/回复页面: http://47.101.153.215:8787/chat?secret=your-secret
管理状态面板: http://47.101.153.215:8787/admin?secret=your-secret
联系人显示设置: http://47.101.153.215:8787/settings?secret=your-secret
远程控制页面: http://47.101.153.215:8787/control?secret=your-secret
健康检查接口: http://47.101.153.215:8787/health
状态 JSON 接口: http://47.101.153.215:8787/api/status?secret=your-secret
```

如果服务器启用了防火墙或云安全组，需要放行 TCP `8787`。如果之后绑定域名和 HTTPS，只需要把上面的 `http://your-server-ip:8787` 换成新的 HTTPS 地址。

If the server firewall or cloud security group is enabled, allow TCP `8787`. If you later bind a domain and HTTPS, replace `http://your-server-ip:8787` with the new HTTPS base URL.

Mac 微信远程回复：

Mac WeChat remote reply:

```sh
python3 tools/mac-wechat-relay.py \
  --poll-url 'http://47.101.153.215:8787/poll?secret=your-secret' \
  --interval 1
```

Mac relay 支持本地失败重试队列，默认保存在：

The Mac relay keeps a local retry queue for failed sends:

```text
~/.barkbridge/pending_replies.json
```

自动发送白名单和目标校验规则保存在：

Auto-send allowlist and target-verification rules are stored at:

```text
~/.barkbridge/contact_rules.json
```

每条规则可配置 `target`、`auto_send`、`aliases` 和 `require_exact_title`。默认要求 OCR 识别到的当前会话标题匹配 `target` 或 `aliases`，否则拦截发送。

Each rule can define `target`, `auto_send`, `aliases`, and `require_exact_title`. By default, the OCR-recognized current chat title must match `target` or one of `aliases`; otherwise the send is blocked.

如果要让 Mac 发送成功或失败后再推一条 Bark 回执，可以传入完整 Bark endpoint：

To send Bark receipts after Mac send success or failure, pass a full Bark endpoint:

```sh
python3 tools/mac-wechat-relay.py \
  --poll-url 'http://47.101.153.215:8787/poll?secret=your-secret' \
  --receipt-url 'https://api.day.app/your-bark-key'
```

Mac relay 会记录阶段化日志：

The Mac relay writes staged logs:

```text
picked: 联系人: 回复内容
sent: 联系人
queued retry 1/5: 联系人
voice-transcribed: 联系人: 转文字内容
```

语音转文字失败时，Mac relay 会保留最近的诊断截图和 OCR 框：

When voice-to-text fails, Mac relay keeps recent diagnostic screenshots and OCR boxes:

```text
~/.barkbridge/voice-debug/
```

自托管管理页会显示最近一次诊断截图路径：

The self-hosted admin page shows the latest diagnostic screenshot path:

```text
http://47.101.153.215:8787/admin?secret=your-secret
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

推送类似 `v1.3.13` 的 tag 后，GitHub Actions 会自动构建 APK 并发布到 GitHub Release 页面。

Pushing a tag such as `v1.3.13` builds APKs and publishes them to the GitHub Release page automatically.
