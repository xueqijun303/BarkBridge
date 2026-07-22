package com.xueqijun.barkbridge

import android.content.Context
import android.content.Intent
import android.os.BatteryManager

object BatteryEvents {
    private const val LAST_POWER_ACTION = "last_power_action"
    private const val LAST_LOW_AT = "last_low_battery_at"
    private const val LOW_DEDUPE_MS = 60 * 60 * 1000L

    fun handle(ctx: Context, intent: Intent) {
        if (!AppSettings.appEnabled(ctx) || !AppSettings.batteryNotificationEnabled(ctx)) return
        when (intent.action) {
            Intent.ACTION_POWER_CONNECTED -> notifyPower(ctx, "充电已连接")
            Intent.ACTION_POWER_DISCONNECTED -> notifyPower(ctx, "充电已断开")
            Intent.ACTION_BATTERY_LOW -> notifyLow(ctx, "系统低电量提醒")
            Intent.ACTION_BATTERY_CHANGED -> notifyChangedIfLow(ctx, intent)
        }
    }

    private fun notifyPower(ctx: Context, text: String) {
        if (Prefs.get(ctx, LAST_POWER_ACTION) == text) return
        Prefs.set(ctx, LAST_POWER_ACTION, text)
        Bark.send(ctx, AppSettings.barkKey(ctx), "电量状态", text)
        LogStore.add(ctx, text, category = "电量")
    }

    private fun notifyLow(ctx: Context, fallback: String) {
        val now = System.currentTimeMillis()
        val last = Prefs.get(ctx, LAST_LOW_AT).toLongOrNull() ?: 0L
        if (now - last < LOW_DEDUPE_MS) return
        Prefs.set(ctx, LAST_LOW_AT, now.toString())
        val threshold = AppSettings.lowBatteryThreshold(ctx).toIntOrNull()?.coerceIn(1, 99) ?: 20
        val level = currentLevel(ctx)
        val body = if (level >= 0) "当前电量 $level%，低于或接近阈值 $threshold%" else fallback
        Bark.send(ctx, AppSettings.barkKey(ctx), "低电量", body)
        LogStore.add(ctx, body, category = "电量")
    }

    private fun notifyChangedIfLow(ctx: Context, intent: Intent) {
        val level = batteryPercent(intent)
        if (level < 0) return
        val plugged = intent.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0) != 0
        val threshold = AppSettings.lowBatteryThreshold(ctx).toIntOrNull()?.coerceIn(1, 99) ?: 20
        if (!plugged && level <= threshold) {
            notifyLow(ctx, "当前电量 $level%，低于阈值 $threshold%")
        }
    }

    private fun batteryPercent(intent: Intent): Int {
        val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        val scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
        if (level < 0 || scale <= 0) return -1
        return (level * 100 / scale.toFloat()).toInt()
    }

    private fun currentLevel(ctx: Context): Int {
        val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as? BatteryManager ?: return -1
        return bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
    }
}
