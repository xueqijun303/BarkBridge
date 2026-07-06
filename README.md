# BarkBridge v1.1

BarkBridge is an Android utility that forwards selected WeChat notifications and incoming-call events to Bark.

## Features

- WeChat notification listener
- WeChat message detail forwarding to Bark
- Incoming-call forwarding to Bark
- Contact-name lookup for incoming calls
- Graphical Bark Key configuration
- Automatic configuration persistence
- Boot startup receiver
- Foreground service
- Notification listener rebind helper
- Wake lock for screen-off operation
- Delayed resend queue for failed Bark requests
- Permission status checks
- Material Design 3 style native UI
- Android 8 to Android 15 target range
- GitHub Actions APK builds
- Optional release signing through local properties or GitHub Secrets

## Current APK

The current APK artifacts are included at:

```text
release/BarkBridge_v1.1-debug.apk
release/BarkBridge_v1.1-release-unsigned.apk
```

Debug APKs can be installed for testing. The unsigned release APK must be signed before public distribution.

Note: v1.1 changes the Android package from `com.example.barkbridge` to `com.xueqijun.barkbridge`, so it installs as a new app instead of upgrading the older debug build.

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

BarkBridge v1.1 is designed to keep forwarding WeChat notifications and incoming-call events while the phone screen is off or locked.

The app uses a foreground service, notification-listener rebinds, wake locks, background network status checks, and a resend queue so Bark pushes can continue during screen-off operation.

Recommended settings:

- Enable BarkBridge notification listener access.
- Allow BarkBridge to ignore battery optimization.
- In Huawei app launch management, enable auto-launch, secondary launch, and background activity.
- Allow WLAN/mobile/background data for BarkBridge.
- Keep the BarkBridge foreground-service notification enabled.

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

Pushing a tag such as `v1.1.0` builds APKs and publishes them to the GitHub Release page automatically.
