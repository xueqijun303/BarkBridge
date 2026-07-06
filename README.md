# BarkBridge v1.2.3

BarkBridge is an Android utility that forwards selected WeChat notifications and incoming-call events to Bark.

## Features

- WeChat notification listener
- WeChat message detail forwarding to Bark
- Incoming-call forwarding to Bark
- Contact-name lookup for incoming calls
- Graphical Bark Key configuration
- Custom Bark server, group, sound, icon, and interruption level
- Automatic configuration persistence
- Boot startup receiver
- Foreground service
- Notification listener rebind helper
- Wake lock for screen-off operation
- Delayed resend queue for failed Bark requests
- WeChat keyword/contact filtering
- Optional group-chat blocking
- Timestamped logs with privacy controls
- Permission status checks
- Material Design 3 style native UI
- Telegram discussion channel entry
- Huawei app launch manual-management shortcut
- Android 8 to Android 15 target range
- GitHub Actions APK builds
- Optional release signing through local properties or GitHub Secrets

## What's New in v1.2.3

- Added a Huawei startup-management shortcut in the permission section.
- The shortcut helps jump to Huawei Phone Manager so BarkBridge can be changed from automatic launch management to manual management.

## What's New in v1.2.2

- Added a "加入讨论" button in the app that opens the BarkBridge Telegram discussion channel.

## What's New in v1.2

- Quieter logs by default. Screen, rebind, duplicate-call, and other troubleshooting records are hidden unless diagnostic mode is enabled.
- Every visible log line includes a timestamp for easier testing.
- Privacy controls can mask phone numbers in logs and disable WeChat message-body logging.
- Bark delivery can be configured with a custom server, group, sound, icon, and interruption level.
- WeChat forwarding rules support blocked keywords, important keywords, allowed contacts/keywords, and optional group-chat blocking.
- The main screen is organized into clearer sections for Bark configuration, permissions, privacy, filters, status, and recent records.

## Current APK

The current APK artifacts are included at:

```text
release/BarkBridge_v1.2.3-debug.apk
release/BarkBridge_v1.2.3-release-unsigned.apk
```

Debug APKs can be installed for testing. The unsigned release APK must be signed before public distribution.

Note: current builds use Android package `com.xueqijun.barkbridge`. Older v1.0 debug builds used `com.example.barkbridge`, so those older APKs install as a separate app instead of upgrading in place.

## Permissions

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

Notification listener access must also be enabled manually in Android settings.

## Screen-Off Delivery

BarkBridge v1.2.3 is designed to keep forwarding WeChat notifications and incoming-call events while the phone screen is off or locked.

The app uses a foreground service, notification-listener rebinds, wake locks, background network status checks, and a resend queue so Bark pushes can continue during screen-off operation.

Recommended settings:

- Enable BarkBridge notification listener access.
- Allow BarkBridge to ignore battery optimization.
- In Huawei app launch management, turn off automatic management for BarkBridge, then manually enable auto-launch, secondary launch, and background activity.
- Allow WLAN/mobile/background data for BarkBridge.
- Keep the BarkBridge foreground-service notification enabled.
- In BarkBridge, enable diagnostic mode only when troubleshooting; normal use can keep it off.

If a temporary network failure occurs, BarkBridge queues failed Bark pushes and resends them when the app is resumed, the device is unlocked, or the foreground service restarts.

## Build

This project is a Gradle Android application:

```sh
./gradlew assembleDebug
```

Release builds are also supported:

```sh
./gradlew assembleRelease
```

Without signing configuration, Gradle produces an unsigned release APK.

## Release Signing

For local release signing, create `local.properties` with:

```properties
BARKBRIDGE_STORE_FILE=/absolute/path/to/barkbridge-release.jks
BARKBRIDGE_STORE_PASSWORD=your_store_password
BARKBRIDGE_KEY_ALIAS=your_key_alias
BARKBRIDGE_KEY_PASSWORD=your_key_password
```

For GitHub Actions signed release builds, configure these repository secrets:

- `BARKBRIDGE_KEYSTORE_BASE64`
- `BARKBRIDGE_STORE_PASSWORD`
- `BARKBRIDGE_KEY_ALIAS`
- `BARKBRIDGE_KEY_PASSWORD`

Generate `BARKBRIDGE_KEYSTORE_BASE64` with:

```sh
base64 -i barkbridge-release.jks
```

## GitHub Releases

Pushing a tag such as `v1.2.3` builds APKs and publishes them to the GitHub Release page automatically.
