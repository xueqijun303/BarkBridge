package com.xueqijun.barkbridge

import android.content.Context
import java.util.Calendar

object QuietHours {
    fun allowsWechat(ctx: Context, fullText: String): Boolean {
        if (!AppSettings.quietHoursEnabled(ctx) || !isNowQuiet(ctx)) return true
        return AppSettings.allowImportantInQuiet(ctx) && RuleEngine.isImportant(ctx, fullText)
    }

    fun allowsCall(ctx: Context): Boolean {
        return !AppSettings.quietHoursEnabled(ctx) ||
            !isNowQuiet(ctx) ||
            AppSettings.allowCallsInQuiet(ctx)
    }

    fun isNowQuiet(ctx: Context): Boolean {
        val start = parseMinutes(AppSettings.quietStart(ctx)) ?: return false
        val end = parseMinutes(AppSettings.quietEnd(ctx)) ?: return false
        val now = Calendar.getInstance()
        val current = now.get(Calendar.HOUR_OF_DAY) * 60 + now.get(Calendar.MINUTE)
        return if (start <= end) {
            current in start until end
        } else {
            current >= start || current < end
        }
    }

    private fun parseMinutes(value: String): Int? {
        val parts = value.trim().split(":")
        if (parts.size != 2) return null
        val hour = parts[0].toIntOrNull() ?: return null
        val minute = parts[1].toIntOrNull() ?: return null
        if (hour !in 0..23 || minute !in 0..59) return null
        return hour * 60 + minute
    }
}

