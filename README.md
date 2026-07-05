# BarkBridge v1.0

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

## Current Release APK

The debug APK is included at:

```text
release/BarkBridge_v1.0-debug.apk
```

This APK uses debug signing. For public distribution, build a release-signed APK with your own keystore.

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

BarkBridge v1.0 is designed to keep forwarding WeChat notifications and incoming-call events while the phone screen is off or locked.

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
gradle assembleDebug
```

The project currently does not include a Gradle wrapper.
