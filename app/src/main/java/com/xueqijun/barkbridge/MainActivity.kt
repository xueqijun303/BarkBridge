package com.xueqijun.barkbridge

import android.Manifest
import android.app.Activity
import android.content.ComponentName
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.PackageInfo
import android.graphics.Color
import android.graphics.Typeface
import android.net.ConnectivityManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.provider.Settings
import android.text.Editable
import android.text.TextWatcher
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

class MainActivity : Activity() {

    private val uiHandler = Handler(Looper.getMainLooper())
    private lateinit var notificationStatus: TextView
    private lateinit var phoneStatus: TextView
    private lateinit var phoneNumberStatus: TextView
    private lateinit var contactsStatus: TextView
    private lateinit var postNotificationStatus: TextView
    private lateinit var batteryStatus: TextView
    private lateinit var backgroundDataStatus: TextView
    private lateinit var serviceStatus: TextView
    private lateinit var pendingStatus: TextView
    private lateinit var logView: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(buildUi())
        BridgeForegroundService.start(this)
    }

    override fun onResume() {
        super.onResume()
        BridgeForegroundService.start(this)
        PendingPushes.flush(this, "activity_resume")
        refreshStatus()
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == RUNTIME_PERMISSION_REQUEST) {
            BridgeForegroundService.start(this)
            refreshStatus()
        }
    }

    private fun buildUi(): View {
        val scroll = ScrollView(this)
        scroll.setBackgroundColor(Surface)

        val root = LinearLayout(this)
        root.orientation = LinearLayout.VERTICAL
        root.setPadding(dp(20), dp(24), dp(20), dp(28))
        scroll.addView(root)

        root.addView(text("BarkBridge", 30f, Color.rgb(17, 29, 28), true))
        root.addView(text("v${appVersionName()} 正式版", 14f, Muted, false).withTop(4))

        val keyCard = card()
        keyCard.addView(text("Bark Key", 16f, OnCard, true))
        val keyInput = EditText(this)
        keyInput.hint = "例如 xxxxxxxxxxxxxxxxxxxx"
        keyInput.setText(Prefs.get(this, "key"))
        keyInput.setSingleLine(true)
        keyInput.textSize = 16f
        keyInput.setPadding(dp(14), dp(8), dp(14), dp(8))
        keyInput.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                Prefs.set(this@MainActivity, "key", s?.toString()?.trim().orEmpty())
                refreshStatus()
            }
            override fun afterTextChanged(s: Editable?) {}
        })
        keyCard.addView(keyInput.withTop(10))
        val testButton = button("发送测试 Bark")
        testButton.setOnClickListener {
            LogStore.add(this, "开始发送测试 Bark")
            Bark.send(this, Prefs.get(this, "key"), "BarkBridge", "v${appVersionName()} 测试推送")
            refreshStatus()
            uiHandler.postDelayed({ refreshStatus() }, 1500)
            uiHandler.postDelayed({ refreshStatus() }, 4000)
        }
        keyCard.addView(testButton.withTop(12))
        root.addView(keyCard.withTop(22))

        val permissionCard = card()
        permissionCard.addView(text("权限检测", 16f, OnCard, true))
        notificationStatus = statusLine()
        phoneStatus = statusLine()
        phoneNumberStatus = statusLine()
        contactsStatus = statusLine()
        postNotificationStatus = statusLine()
        batteryStatus = statusLine()
        backgroundDataStatus = statusLine()
        serviceStatus = statusLine()
        pendingStatus = statusLine()
        permissionCard.addView(notificationStatus.withTop(12))
        permissionCard.addView(phoneStatus.withTop(8))
        permissionCard.addView(phoneNumberStatus.withTop(8))
        permissionCard.addView(contactsStatus.withTop(8))
        permissionCard.addView(postNotificationStatus.withTop(8))
        permissionCard.addView(batteryStatus.withTop(8))
        permissionCard.addView(backgroundDataStatus.withTop(8))
        permissionCard.addView(serviceStatus.withTop(8))
        permissionCard.addView(pendingStatus.withTop(8))

        val listenerButton = button("开启微信通知监听权限")
        listenerButton.setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }
        permissionCard.addView(listenerButton.withTop(14))

        val runtimeButton = button("授予电话/通知权限")
        runtimeButton.setOnClickListener { requestMissingRuntimePermissions() }
        permissionCard.addView(runtimeButton.withTop(8))

        val restartCallButton = button("重启来电监听")
        restartCallButton.setOnClickListener {
            LogStore.add(this, "手动重启来电监听")
            BridgeForegroundService.start(this)
            refreshStatus()
            uiHandler.postDelayed({ refreshStatus() }, 1200)
        }
        permissionCard.addView(restartCallButton.withTop(8))

        val batteryButton = button("允许忽略电池优化")
        batteryButton.setOnClickListener { requestIgnoreBatteryOptimizations() }
        permissionCard.addView(batteryButton.withTop(8))

        val backgroundDataButton = button("允许后台联网")
        backgroundDataButton.setOnClickListener { openBackgroundDataSettings() }
        permissionCard.addView(backgroundDataButton.withTop(8))

        val appSettingsButton = button("打开应用后台设置")
        appSettingsButton.setOnClickListener { openAppSettings() }
        permissionCard.addView(appSettingsButton.withTop(8))
        root.addView(permissionCard.withTop(14))

        val featureCard = card()
        featureCard.addView(text("功能状态", 16f, OnCard, true))
        featureCard.addView(text("微信通知监听 / 消息详情推送 Bark", 14f, OnCard, false).withTop(12))
        featureCard.addView(text("来电推送 Bark / 后台常驻服务", 14f, OnCard, false).withTop(8))
        featureCard.addView(text("配置自动保存 / 开机自启动", 14f, OnCard, false).withTop(8))
        val releaseButton = button("查看 GitHub 最新版本")
        releaseButton.setOnClickListener { openLatestRelease() }
        featureCard.addView(releaseButton.withTop(12))
        root.addView(featureCard.withTop(14))

        val logCard = card()
        logCard.addView(text("最近记录", 16f, OnCard, true))
        logView = text("", 13f, Muted, false)
        logCard.addView(logView.withTop(10))
        val clearLogButton = button("清空日志")
        clearLogButton.setOnClickListener {
            LogStore.clear(this)
            refreshStatus()
        }
        logCard.addView(clearLogButton.withTop(12))
        root.addView(logCard.withTop(14))

        return scroll
    }

    private fun refreshStatus() {
        notificationStatus.text = marker(isNotificationListenerEnabled()) + " 微信通知监听"
        phoneStatus.text = marker(hasPhoneStatePermission()) + " 电话状态权限"
        phoneNumberStatus.text = marker(hasCallNumberPermission()) + " 来电号码权限"
        contactsStatus.text = marker(hasContactsPermission()) + " 联系人匹配权限"
        postNotificationStatus.text = marker(hasPostNotificationPermission()) + " 前台服务通知权限"
        batteryStatus.text = marker(isIgnoringBatteryOptimizations()) + " 忽略电池优化"
        backgroundDataStatus.text = marker(isBackgroundDataAllowed()) + " 后台联网不受限"
        serviceStatus.text = marker(Prefs.get(this, "key").isNotBlank()) + " Bark Key 已配置"
        pendingStatus.text = "待补发 ${PendingPushes.count(this)} 条"
        logView.text = LogStore.get(this).ifBlank { "暂无记录" }
    }

    private fun requestMissingRuntimePermissions() {
        val permissions = mutableListOf<String>()
        if (!hasPhoneStatePermission()) {
            permissions.add(Manifest.permission.READ_PHONE_STATE)
        }
        if (!hasPermission(Manifest.permission.READ_CALL_LOG)) {
            permissions.add(Manifest.permission.READ_CALL_LOG)
        }
        if (!hasPermission(Manifest.permission.READ_PHONE_NUMBERS)) {
            permissions.add(Manifest.permission.READ_PHONE_NUMBERS)
        }
        if (!hasContactsPermission()) {
            permissions.add(Manifest.permission.READ_CONTACTS)
        }
        if (!hasPostNotificationPermission() && Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        if (permissions.isNotEmpty()) {
            requestPermissions(permissions.toTypedArray(), RUNTIME_PERMISSION_REQUEST)
        } else {
            LogStore.add(this, "电话/通知权限已授予，正在重启监听")
            BridgeForegroundService.start(this)
            refreshStatus()
        }
    }

    private fun hasPhoneStatePermission(): Boolean {
        return hasPermission(Manifest.permission.READ_PHONE_STATE)
    }

    private fun hasCallNumberPermission(): Boolean {
        return hasPermission(Manifest.permission.READ_CALL_LOG) ||
            hasPermission(Manifest.permission.READ_PHONE_NUMBERS)
    }

    private fun hasContactsPermission(): Boolean {
        return hasPermission(Manifest.permission.READ_CONTACTS)
    }

    private fun hasPermission(permission: String): Boolean {
        return checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED
    }

    private fun hasPostNotificationPermission(): Boolean {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
    }

    private fun isNotificationListenerEnabled(): Boolean {
        val flat = Settings.Secure.getString(contentResolver, "enabled_notification_listeners") ?: return false
        val target = ComponentName(this, NotifyService::class.java).flattenToString()
        val legacyTarget = packageName
        return flat.split(":").any { it.equals(target, true) || it.contains(legacyTarget, true) }
    }

    private fun isIgnoringBatteryOptimizations(): Boolean {
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        return pm.isIgnoringBatteryOptimizations(packageName)
    }

    private fun requestIgnoreBatteryOptimizations() {
        try {
            val intent = Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
            intent.data = Uri.parse("package:$packageName")
            startActivity(intent)
        } catch (e: Exception) {
            startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
        }
    }

    private fun isBackgroundDataAllowed(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return true
        val cm = getSystemService(CONNECTIVITY_SERVICE) as ConnectivityManager
        return cm.restrictBackgroundStatus != ConnectivityManager.RESTRICT_BACKGROUND_STATUS_ENABLED
    }

    private fun openBackgroundDataSettings() {
        try {
            val intent = Intent(Settings.ACTION_IGNORE_BACKGROUND_DATA_RESTRICTIONS_SETTINGS)
            intent.data = Uri.parse("package:$packageName")
            startActivity(intent)
        } catch (e: Exception) {
            openAppSettings()
        }
    }

    private fun openAppSettings() {
        val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
        intent.data = Uri.parse("package:$packageName")
        startActivity(intent)
    }

    private fun openLatestRelease() {
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://github.com/xueqijun303/BarkBridge/releases"))
        startActivity(intent)
    }

    private fun appVersionName(): String {
        return try {
            val info: PackageInfo = packageManager.getPackageInfo(packageName, 0)
            info.versionName ?: "1.1"
        } catch (e: Exception) {
            "1.1"
        }
    }

    private fun marker(ok: Boolean): String = if (ok) "OK" else "未开启"

    private fun card(): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(16), dp(18), dp(16))
            background = android.graphics.drawable.GradientDrawable().apply {
                color = android.content.res.ColorStateList.valueOf(Color.WHITE)
                cornerRadius = dp(8).toFloat()
                setStroke(1, Color.rgb(222, 229, 227))
            }
        }
    }

    private fun button(label: String): Button {
        return Button(this).apply {
            text = label
            textSize = 14f
            isAllCaps = false
            gravity = Gravity.CENTER
            setTextColor(Color.WHITE)
            setBackgroundColor(Primary)
            minHeight = dp(46)
        }
    }

    private fun statusLine(): TextView = text("", 14f, OnCard, false)

    private fun text(value: String, size: Float, color: Int, bold: Boolean): TextView {
        return TextView(this).apply {
            text = value
            textSize = size
            setTextColor(color)
            includeFontPadding = true
            if (bold) typeface = Typeface.DEFAULT_BOLD
        }
    }

    private fun View.withTop(top: Int): View {
        layoutParams = LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        ).apply { topMargin = dp(top) }
        return this
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    companion object {
        private const val RUNTIME_PERMISSION_REQUEST = 1001
        private val Surface = Color.rgb(247, 250, 249)
        private val Primary = Color.rgb(0, 106, 106)
        private val OnCard = Color.rgb(25, 32, 31)
        private val Muted = Color.rgb(82, 96, 94)
    }
}
