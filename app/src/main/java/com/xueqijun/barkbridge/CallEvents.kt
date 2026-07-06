package com.xueqijun.barkbridge

import android.content.Context

object CallEvents {
    private const val LAST_CALL_AT = "last_call_at"
    private const val LAST_CALL_NUMBER = "last_call_number"
    private const val DEDUPE_WINDOW_MS = 8000L

    fun notifyIncoming(ctx: Context, number: String, source: String) {
        val normalized = number.ifBlank { "未知号码" }
        val display = ContactNames.displayFor(ctx, normalized)
        val now = System.currentTimeMillis()
        val lastAt = Prefs.get(ctx, LAST_CALL_AT).toLongOrNull() ?: 0L
        val lastNumber = Prefs.get(ctx, LAST_CALL_NUMBER)
        if (normalized == lastNumber && now - lastAt < DEDUPE_WINDOW_MS) {
            LogStore.add(ctx, "来电忽略重复事件: $source $normalized", diagnostic = true)
            return
        }

        Prefs.set(ctx, LAST_CALL_AT, now.toString())
        Prefs.set(ctx, LAST_CALL_NUMBER, normalized)
        Bark.send(ctx, Prefs.get(ctx, "key"), "来电", display)
        LogStore.add(ctx, "来电: $display ($source)")
    }
}
