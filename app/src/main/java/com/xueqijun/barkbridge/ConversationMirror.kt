package com.xueqijun.barkbridge

import android.content.Context
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

object ConversationMirror {
    fun recordIncoming(ctx: Context, contact: String, text: String, mediaType: String = "", requestTranscription: Boolean = false) {
        if (!AppSettings.conversationMirrorEnabled(ctx)) return
        val endpoint = AppSettings.conversationIngestUrl(ctx)
        if (endpoint.isBlank() || contact.isBlank() || text.isBlank()) return
        val secret = relaySecret(ctx)
        if (secret.isBlank()) {
            LogStore.add(ctx, "聊天面板未上传: 缺少 relay secret", diagnostic = true, category = "聊天")
            return
        }

        Thread {
            var conn: HttpURLConnection? = null
            try {
                val body = JSONObject()
                    .put("secret", secret)
                    .put("contact", contact)
                    .put("text", text)
                    .put("direction", "incoming")
                    .put("source", "android")
                    .put("mediaType", mediaType)
                    .put("requestTranscription", requestTranscription)
                    .put("createdAt", System.currentTimeMillis())
                    .toString()
                    .toByteArray(Charsets.UTF_8)
                conn = URL(endpoint).openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.connectTimeout = 10000
                conn.readTimeout = 10000
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                conn.setRequestProperty("User-Agent", "BarkBridge/1.3.12 Android")
                conn.outputStream.use { it.write(body) }
                val code = conn.responseCode
                if (code !in 200..299) {
                    val detail = try {
                        (conn.errorStream ?: conn.inputStream)?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                    } catch (e: Exception) {
                        ""
                    }
                    val suffix = if (detail.isBlank()) "" else " ${detail.take(80)}"
                    LogStore.add(ctx, "聊天面板上传失败: HTTP $code$suffix", category = "聊天")
                } else {
                    LogStore.add(ctx, "聊天面板已上传: $contact", category = "聊天")
                }
            } catch (e: Exception) {
                LogStore.add(ctx, "聊天面板上传失败: ${e.javaClass.simpleName} ${e.message.orEmpty()}".take(180), category = "聊天")
            } finally {
                conn?.disconnect()
            }
        }.start()
    }

    fun chatUrl(ctx: Context, contact: String): String {
        val base = AppSettings.conversationChatPageUrl(ctx)
        val secret = relaySecret(ctx)
        if (base.isBlank() || secret.isBlank()) return ""
        val sep = if (base.contains("?")) "&" else "?"
        return "$base${sep}secret=${enc(secret)}&contact=${enc(contact)}"
    }

    private fun relaySecret(ctx: Context): String {
        return AppSettings.conversationRelaySecret(ctx)
            .ifBlank { queryParam(AppSettings.conversationChatPageUrl(ctx), "secret") }
            .ifBlank { queryParam(AppSettings.conversationIngestUrl(ctx), "secret") }
            .ifBlank { queryParam(AppSettings.remoteReplyPageUrl(ctx), "secret") }
            .ifBlank { queryParam(AppSettings.remoteReplyPollUrl(ctx), "secret") }
    }

    private fun queryParam(rawUrl: String, name: String): String {
        val query = rawUrl.substringAfter("?", "")
        if (query.isBlank()) return ""
        return query.split("&").firstNotNullOfOrNull { part ->
            val key = part.substringBefore("=")
            val value = part.substringAfter("=", "")
            if (key == name) java.net.URLDecoder.decode(value, "UTF-8") else null
        }.orEmpty()
    }

    private fun enc(value: String): String {
        return URLEncoder.encode(value, "UTF-8").replace("+", "%20")
    }
}
