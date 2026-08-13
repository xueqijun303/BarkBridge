
package com.xueqijun.barkbridge

import android.app.Notification
import android.provider.Telephony
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

class NotifyService: NotificationListenerService() {

    override fun onListenerConnected() {
        super.onListenerConnected()
        LogStore.add(applicationContext, "微信通知监听已连接")
        BridgeForegroundService.start(applicationContext)
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        LogStore.add(applicationContext, "微信通知监听已断开，等待系统重绑")
        BridgeForegroundService.start(applicationContext)
    }

    override fun onCreate() {
        super.onCreate()
        BridgeForegroundService.start(applicationContext)
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {

        if (sbn.packageName == packageName) return
        if(sbn.packageName!="com.tencent.mm") {
            handleOtherNotification(sbn)
            return
        }
        if (!AppSettings.appEnabled(applicationContext) || !AppSettings.wechatEnabled(applicationContext)) {
            LogStore.add(applicationContext, "已关闭微信接收，忽略微信通知", diagnostic = true, category = "微信")
            return
        }

        val e = sbn.notification.extras
        val title = e.getCharSequence(Notification.EXTRA_TITLE)?.toString()?:""
        val text = e.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()
            ?: e.getCharSequence(Notification.EXTRA_TEXT)?.toString()
            ?: ""

        val full = "$title $text"
        if (!QuietHours.allowsWechat(applicationContext, full)) {
            LogStore.add(applicationContext, "勿扰时段忽略微信通知", diagnostic = true, category = "微信")
            return
        }

        if(RuleEngine.shouldDrop(applicationContext, title, text)) {
            LogStore.add(applicationContext, "微信通知已按规则过滤", diagnostic = true, category = "微信")
            return
        }

        val key = AppSettings.barkKey(applicationContext)

        val msg = if(RuleEngine.isImportant(applicationContext, full))
            "🔥 "+AI.summary(full)
        else
            AI.summary(full)

        val pushTitle = if (title.isBlank()) "微信消息" else "微信 - $title"
        val replyUrl = RemoteReplyRegistry.capture(applicationContext, sbn, title, text)
        ConversationMirror.recordIncoming(applicationContext, title.ifBlank { "微信" }, text)
        val chatUrl = ConversationMirror.chatUrl(applicationContext, title.ifBlank { "微信" })
        if (replyUrl.isNullOrBlank()) {
            if (chatUrl.isBlank()) {
                Bark.send(applicationContext,key,pushTitle,msg)
            } else {
                Bark.send(applicationContext, key, pushTitle, "$msg\n\n点击通知查看完整会话\n$chatUrl", mapOf("url" to chatUrl))
            }
        } else {
            val openUrl = chatUrl.ifBlank { replyUrl }
            Bark.send(applicationContext, key, pushTitle, "$msg\n\n查看完整会话\n${openUrl}\n\n直接回复\n$replyUrl", mapOf("url" to openUrl))
        }

        val logText = if (AppSettings.saveMessageBody(applicationContext)) {
            full
        } else {
            "微信消息已推送"
        }
        LogStore.add(applicationContext, logText, category = "微信")
    }

    private fun handleOtherNotification(sbn: StatusBarNotification) {
        if (!AppSettings.appEnabled(applicationContext)) return

        val e = sbn.notification.extras
        val title = e.getCharSequence(Notification.EXTRA_TITLE)?.toString().orEmpty()
        val text = e.getCharSequence(Notification.EXTRA_TEXT)?.toString().orEmpty()
        val full = "$title $text".trim()
        if (full.isBlank()) return

        if (isSmsNotification(sbn)) {
            if (!AppSettings.smsNotificationEnabled(applicationContext)) return
            Bark.send(applicationContext, AppSettings.barkKey(applicationContext), "短信 - ${title.ifBlank { appLabel(sbn.packageName) }}", AI.summary(full))
            LogStore.add(applicationContext, "短信通知: $full", category = "短信")
            return
        }

        if (!AppSettings.generalNotificationEnabled(applicationContext)) return
        if (!allowedGeneralPackage(sbn.packageName)) return

        val label = appLabel(sbn.packageName)
        Bark.send(applicationContext, AppSettings.barkKey(applicationContext), "$label 通知", AI.summary(full))
        LogStore.add(applicationContext, "$label: $full", category = "App")
    }

    private fun isSmsNotification(sbn: StatusBarNotification): Boolean {
        val pkg = sbn.packageName.lowercase()
        val defaultSms = try {
            Telephony.Sms.getDefaultSmsPackage(applicationContext).orEmpty().lowercase()
        } catch (e: Exception) {
            ""
        }
        if (defaultSms.isNotBlank() && pkg == defaultSms) return true
        return pkg.contains("mms") ||
            pkg.contains("messaging") ||
            pkg.contains("message")
    }

    private fun allowedGeneralPackage(pkg: String): Boolean {
        return AppSettings.keywordList(AppSettings.generalNotificationPackages(applicationContext))
            .any { it.equals(pkg, ignoreCase = true) }
    }

    private fun appLabel(pkg: String): String {
        return try {
            val info = packageManager.getApplicationInfo(pkg, 0)
            packageManager.getApplicationLabel(info).toString()
        } catch (e: Exception) {
            pkg
        }
    }
}
