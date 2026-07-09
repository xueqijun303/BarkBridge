
package com.xueqijun.barkbridge

import android.app.Notification
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

        if(sbn.packageName!="com.tencent.mm") return
        if (!AppSettings.appEnabled(applicationContext)) {
            LogStore.add(applicationContext, "已关闭接收，忽略微信通知", diagnostic = true)
            return
        }

        val e = sbn.notification.extras
        val title = e.getCharSequence(Notification.EXTRA_TITLE)?.toString()?:""
        val text = e.getCharSequence(Notification.EXTRA_TEXT)?.toString()?:""

        val full = "$title $text"

        if(RuleEngine.shouldDrop(applicationContext, title, text)) {
            LogStore.add(applicationContext, "微信通知已按规则过滤", diagnostic = true)
            return
        }

        val key = AppSettings.barkKey(applicationContext)

        val msg = if(RuleEngine.isImportant(applicationContext, full))
            "🔥 "+AI.summary(full)
        else
            AI.summary(full)

        Bark.send(applicationContext,key,"微信消息",msg)

        val logText = if (AppSettings.saveMessageBody(applicationContext)) {
            full
        } else {
            "微信消息已推送"
        }
        LogStore.add(applicationContext, logText)
    }
}
