package com.xueqijun.barkbridge

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

object PendingConversationUploads {
    private const val KEY = "pending_conversation_uploads"
    private const val MAX_ITEMS = 80

    fun add(ctx: Context, item: JSONObject) {
        if (!AppSettings.appEnabled(ctx)) return

        val list = read(ctx)
        list.put(item)
        val trimmed = JSONArray()
        val start = (list.length() - MAX_ITEMS).coerceAtLeast(0)
        for (i in start until list.length()) {
            trimmed.put(list.getJSONObject(i))
        }
        Prefs.set(ctx, KEY, trimmed.toString())
        LogStore.add(ctx, "聊天面板已加入待补发队列: ${item.optString("contact")}", category = "聊天")
    }

    fun flush(ctx: Context, reason: String) {
        if (!AppSettings.appEnabled(ctx) || !AppSettings.conversationMirrorEnabled(ctx)) return

        val list = read(ctx)
        if (list.length() == 0) return

        Prefs.set(ctx, KEY, "")
        LogStore.add(ctx, "开始补发 ${list.length()} 条聊天面板记录: $reason", category = "聊天")
        val failed = JSONArray()
        for (i in 0 until list.length()) {
            val item = list.getJSONObject(i)
            if (!ConversationMirror.upload(ctx, item, queueOnFailure = false)) {
                failed.put(item)
            }
        }
        if (failed.length() > 0) {
            Prefs.set(ctx, KEY, failed.toString())
            LogStore.add(ctx, "聊天面板仍有 ${failed.length()} 条待补发", category = "聊天")
        }
    }

    fun count(ctx: Context): Int {
        return read(ctx).length()
    }

    private fun read(ctx: Context): JSONArray {
        val raw = Prefs.get(ctx, KEY)
        if (raw.isBlank()) return JSONArray()
        return try {
            JSONArray(raw)
        } catch (e: Exception) {
            JSONArray()
        }
    }
}
