package com.xueqijun.barkbridge

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Collections

object RemoteReplyPoller {
    @Volatile private var running = false
    private val handled = Collections.synchronizedSet(mutableSetOf<String>())

    fun start(ctx: Context) {
        if (running) return
        running = true
        Thread {
            while (running) {
                try {
                    if (AppSettings.appEnabled(ctx) &&
                        AppSettings.remoteReplyEnabled(ctx) &&
                        AppSettings.remoteReplyTarget(ctx) != "mac") {
                        pollOnce(ctx.applicationContext)
                    }
                } catch (e: Exception) {
                    LogStore.add(ctx, "远程回复轮询失败: ${e.javaClass.simpleName} ${e.message.orEmpty()}".take(180), diagnostic = true, category = "回复")
                }
                Thread.sleep(intervalMs(ctx))
            }
        }.start()
    }

    fun stop() {
        running = false
    }

    private fun pollOnce(ctx: Context) {
        val pollUrl = AppSettings.remoteReplyPollUrl(ctx)
        if (pollUrl.isBlank()) return

        var conn: HttpURLConnection? = null
        try {
            conn = URL(pollUrl).openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.connectTimeout = 10000
            conn.readTimeout = 10000
            conn.setRequestProperty("User-Agent", "BarkBridge/1.3 Android")
            if (conn.responseCode !in 200..299) return
            val body = conn.inputStream.bufferedReader().use { it.readText() }.trim()
            if (body.isBlank()) return
            parseReplies(body).forEach { reply ->
                val id = reply.optString("id").ifBlank { "${reply.optString("token")}:${reply.optString("text")}" }
                if (!handled.add(id)) return@forEach
                RemoteReplyRegistry.send(ctx, reply.optString("token"), reply.optString("text"))
            }
        } finally {
            conn?.disconnect()
        }
    }

    private fun parseReplies(body: String): List<JSONObject> {
        val first = body.firstOrNull() ?: return emptyList()
        return when (first) {
            '[' -> {
                val arr = JSONArray(body)
                (0 until arr.length()).mapNotNull { arr.optJSONObject(it) }
            }
            '{' -> {
                val obj = JSONObject(body)
                val replies = obj.optJSONArray("replies")
                if (replies != null) {
                    (0 until replies.length()).mapNotNull { replies.optJSONObject(it) }
                } else if (obj.has("token") && obj.has("text")) {
                    listOf(obj)
                } else {
                    emptyList()
                }
            }
            else -> emptyList()
        }
    }

    private fun intervalMs(ctx: Context): Long {
        val seconds = AppSettings.remoteReplyPollSeconds(ctx).toLongOrNull()?.coerceIn(5, 300) ?: 20L
        return seconds * 1000L
    }
}
