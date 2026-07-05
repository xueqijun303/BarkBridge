package com.example.barkbridge

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.service.notification.NotificationListenerService

class BridgeForegroundService : Service() {

    private val handler = Handler(Looper.getMainLooper())
    private var callService: CallService? = null
    private val screenReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val action = intent.action ?: return
            LogStore.add(context, "屏幕状态: $action")
            PendingPushes.flush(context, action)
            requestNotificationListenerRebind(context)
        }
    }
    private val rebindRunnable = object : Runnable {
        override fun run() {
            requestNotificationListenerRebind(applicationContext)
            handler.postDelayed(this, REBIND_INTERVAL_MS)
        }
    }

    override fun onCreate() {
        super.onCreate()
        createChannel()
        startForeground(NOTIFICATION_ID, buildNotification())
        WakeLocks.acquireServiceLock(applicationContext)
        callService = CallService(applicationContext).also { it.start() }
        registerScreenReceiver()
        requestNotificationListenerRebind(applicationContext)
        PendingPushes.flush(applicationContext, "service_start")
        handler.postDelayed(rebindRunnable, REBIND_INTERVAL_MS)
        LogStore.add(applicationContext, "后台常驻服务已启动")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        callService?.start()
        return START_STICKY
    }

    override fun onDestroy() {
        handler.removeCallbacks(rebindRunnable)
        try {
            unregisterReceiver(screenReceiver)
        } catch (e: Exception) {
            LogStore.add(applicationContext, "屏幕监听注销失败: ${e.javaClass.simpleName}")
        }
        WakeLocks.releaseServiceLock(applicationContext)
        callService?.stop()
        callService = null
        LogStore.add(applicationContext, "后台常驻服务已停止")
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun buildNotification(): android.app.Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or immutableFlag()
        )
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            android.app.Notification.Builder(this, CHANNEL_ID)
        } else {
            android.app.Notification.Builder(this)
        }
        return builder
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentTitle("BarkBridge 正在运行")
            .setContentText("保持息屏监听微信和来电")
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            "BarkBridge 后台服务",
            NotificationManager.IMPORTANCE_LOW
        )
        channel.description = "保持 BarkBridge 后台监听"
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun registerScreenReceiver() {
        val filter = IntentFilter().apply {
            addAction(Intent.ACTION_SCREEN_ON)
            addAction(Intent.ACTION_SCREEN_OFF)
            addAction(Intent.ACTION_USER_PRESENT)
        }
        registerReceiver(screenReceiver, filter)
    }

    companion object {
        private const val CHANNEL_ID = "bark_bridge_foreground"
        private const val NOTIFICATION_ID = 100
        private const val REBIND_INTERVAL_MS = 15 * 60 * 1000L

        fun start(context: Context) {
            val intent = Intent(context, BridgeForegroundService::class.java)
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(intent)
                } else {
                    context.startService(intent)
                }
            } catch (e: Exception) {
                LogStore.add(context, "后台服务启动失败: ${e.javaClass.simpleName}")
            }
        }

        fun requestNotificationListenerRebind(context: Context) {
            if (Build.VERSION.SDK_INT < Build.VERSION_CODES.N) return
            try {
                val component = ComponentName(context, NotifyService::class.java)
                NotificationListenerService.requestRebind(component)
                LogStore.add(context, "已请求重绑微信通知监听")
            } catch (e: Exception) {
                LogStore.add(context, "重绑通知监听失败: ${e.javaClass.simpleName}")
            }
        }

        private fun immutableFlag(): Int {
            return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) PendingIntent.FLAG_IMMUTABLE else 0
        }
    }
}
