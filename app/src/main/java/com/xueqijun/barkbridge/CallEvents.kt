package com.xueqijun.barkbridge

import android.content.Context

object CallEvents {
    private const val LAST_CALL_AT = "last_call_at"
    private const val LAST_CALL_NUMBER = "last_call_number"
    private const val DEDUPE_WINDOW_MS = 8000L

    fun notifyIncoming(ctx: Context, number: String, source: String) {
        if (!AppSettings.appEnabled(ctx) || !AppSettings.callEnabled(ctx)) {
            LogStore.add(ctx, "已关闭来电接收，忽略来电事件: $source", diagnostic = true, category = "来电")
            return
        }
        if (!QuietHours.allowsCall(ctx)) {
            LogStore.add(ctx, "勿扰时段忽略来电事件: $source", diagnostic = true, category = "来电")
            return
        }

        val normalized = number.ifBlank { "未知号码" }
        val display = ContactNames.displayFor(ctx, normalized)
        val now = System.currentTimeMillis()
        val lastAt = Prefs.get(ctx, LAST_CALL_AT).toLongOrNull() ?: 0L
        val lastNumber = Prefs.get(ctx, LAST_CALL_NUMBER)
        if (normalized == lastNumber && now - lastAt < DEDUPE_WINDOW_MS) {
            LogStore.add(ctx, "来电忽略重复事件: $source $normalized", diagnostic = true, category = "来电")
            return
        }

        Prefs.set(ctx, LAST_CALL_AT, now.toString())
        Prefs.set(ctx, LAST_CALL_NUMBER, normalized)
        Bark.send(ctx, Prefs.get(ctx, "key"), "来电", "$display\n来源: $source")
        LogStore.add(ctx, "来电: $display ($source)", category = "来电")
    }

    fun notifyMissed(ctx: Context, number: String, source: String) {
        if (!AppSettings.appEnabled(ctx) || !AppSettings.callEnabled(ctx) || !AppSettings.missedCallEnabled(ctx)) {
            LogStore.add(ctx, "已关闭未接来电提醒，忽略事件: $source", diagnostic = true, category = "来电")
            return
        }
        if (!QuietHours.allowsCall(ctx)) {
            LogStore.add(ctx, "勿扰时段忽略未接来电: $source", diagnostic = true, category = "来电")
            return
        }

        val normalized = number.ifBlank { "未知号码" }
        val display = ContactNames.displayFor(ctx, normalized)
        Bark.send(ctx, Prefs.get(ctx, "key"), "未接来电", "$display\n来源: $source")
        LogStore.add(ctx, "未接来电: $display ($source)", category = "来电")
    }
}
