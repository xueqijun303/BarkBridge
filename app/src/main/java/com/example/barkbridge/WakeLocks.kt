package com.example.barkbridge

import android.content.Context
import android.os.PowerManager

object WakeLocks {
    private const val SEND_TIMEOUT_MS = 20_000L
    private var serviceLock: PowerManager.WakeLock? = null

    fun acquireServiceLock(ctx: Context) {
        if (serviceLock?.isHeld == true) return
        try {
            val pm = ctx.getSystemService(Context.POWER_SERVICE) as PowerManager
            serviceLock = pm.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "BarkBridge:ForegroundService"
            ).apply {
                setReferenceCounted(false)
                acquire()
            }
            LogStore.add(ctx, "息屏保持已启用")
        } catch (e: Exception) {
            LogStore.add(ctx, "息屏保持启用失败: ${e.javaClass.simpleName}")
        }
    }

    fun releaseServiceLock(ctx: Context) {
        try {
            serviceLock?.takeIf { it.isHeld }?.release()
            serviceLock = null
            LogStore.add(ctx, "息屏保持已释放")
        } catch (e: Exception) {
            LogStore.add(ctx, "息屏保持释放失败: ${e.javaClass.simpleName}")
        }
    }

    fun acquireSendLock(ctx: Context): PowerManager.WakeLock? {
        return try {
            val pm = ctx.getSystemService(Context.POWER_SERVICE) as PowerManager
            pm.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "BarkBridge:Send"
            ).apply {
                setReferenceCounted(false)
                acquire(SEND_TIMEOUT_MS)
            }
        } catch (e: Exception) {
            LogStore.add(ctx, "发送唤醒失败: ${e.javaClass.simpleName}")
            null
        }
    }
}
