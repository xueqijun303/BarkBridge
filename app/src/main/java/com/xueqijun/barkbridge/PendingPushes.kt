package com.xueqijun.barkbridge

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

object PendingPushes {
    private const val KEY = "pending_pushes"
    private const val MAX_ITEMS = 30

    fun add(ctx: Context, title: String, body: String) {
        val list = read(ctx)
        list.put(JSONObject().apply {
            put("title", title)
            put("body", body)
            put("time", System.currentTimeMillis())
        })
        val trimmed = JSONArray()
        val start = (list.length() - MAX_ITEMS).coerceAtLeast(0)
        for (i in start until list.length()) {
            trimmed.put(list.getJSONObject(i))
        }
        Prefs.set(ctx, KEY, trimmed.toString())
        LogStore.add(ctx, "已加入待补发队列: $title")
    }

    fun flush(ctx: Context, reason: String) {
        val key = Prefs.get(ctx, "key")
        val list = read(ctx)
        if (list.length() == 0 || key.isBlank()) return

        Prefs.set(ctx, KEY, "")
        LogStore.add(ctx, "开始补发 ${list.length()} 条 Bark: $reason")
        for (i in 0 until list.length()) {
            val item = list.getJSONObject(i)
            Bark.send(ctx, key, item.optString("title"), item.optString("body"), queueOnFailure = true)
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
