
package com.xueqijun.barkbridge

import android.content.Context
import java.net.URL
import java.net.HttpURLConnection
import java.net.URLEncoder

object Bark {

    fun send(ctx: Context, key: String, title: String, body: String, queueOnFailure: Boolean = true) {
        val config = key.trim()
        if (config.isBlank()) {
            LogStore.add(ctx, "Bark 推送失败: Bark Key 为空", category = "Bark")
            return
        }

        Thread{
            val wakeLock = WakeLocks.acquireSendLock(ctx)
            var conn: HttpURLConnection? = null
            try{
                val url = URL(buildUrl(ctx, config, title, body))
                conn = url.openConnection() as HttpURLConnection
                conn.requestMethod="GET"
                conn.connectTimeout=10000
                conn.readTimeout=10000
                conn.setRequestProperty("User-Agent", "BarkBridge/1.2 Android")

                val code = conn.responseCode
                val response = readResponse(conn)
                if(code in 200..299){
                    LogStore.add(ctx, "Bark 推送成功: HTTP $code", category = "Bark")
                }else{
                    LogStore.add(ctx, "Bark 推送失败: HTTP $code ${response.take(160)}", category = "Bark")
                    if (queueOnFailure) PendingPushes.add(ctx, title, body)
                }
            }catch(e:Exception){
                LogStore.add(ctx, "Bark 推送失败: ${e.javaClass.simpleName} ${e.message.orEmpty()}".take(220), category = "Bark")
                if (queueOnFailure) PendingPushes.add(ctx, title, body)
            }finally{
                conn?.disconnect()
                wakeLock?.takeIf { it.isHeld }?.release()
            }
        }.start()
    }

    fun send(key:String,title:String,body:String){
        if(key.isBlank()) return
        Thread{
            try{
                val url = URL(buildUrl(null, key.trim(), title, body))
                val conn = url.openConnection() as HttpURLConnection
                conn.requestMethod="GET"
                conn.connectTimeout=10000
                conn.readTimeout=10000
                conn.inputStream.close()
                conn.disconnect()
            }catch(e:Exception){}
        }.start()
    }

    private fun buildUrl(ctx: Context?, config: String, title: String, body: String): String {
        val base = if(config.startsWith("http://") || config.startsWith("https://")){
            config.trimEnd('/')
        }else{
            val server = ctx?.let { AppSettings.barkServer(it) } ?: "https://api.day.app"
            "${server.trimEnd('/')}/${encode(config)}"
        }
        val query = ctx?.let { barkQuery(it) }.orEmpty()
        return "$base/${encode(title)}/${encode(body)}$query"
    }

    private fun encode(value: String): String {
        return URLEncoder.encode(value, "UTF-8").replace("+", "%20")
    }

    private fun barkQuery(ctx: Context): String {
        val params = mutableListOf<Pair<String, String>>()
        val group = AppSettings.barkGroup(ctx)
        if (group.isNotBlank()) params.add("group" to group)
        val sound = AppSettings.barkSound(ctx)
        if (sound.isNotBlank()) params.add("sound" to sound)
        val icon = AppSettings.barkIcon(ctx)
        if (icon.isNotBlank()) params.add("icon" to icon)
        val level = AppSettings.barkLevel(ctx)
        if (level.isNotBlank()) params.add("level" to level)
        if (params.isEmpty()) return ""
        return params.joinToString(prefix = "?", separator = "&") { "${encode(it.first)}=${encode(it.second)}" }
    }

    private fun readResponse(conn: HttpURLConnection): String {
        val stream = if(conn.responseCode in 200..299) conn.inputStream else conn.errorStream
        return stream?.bufferedReader()?.use { it.readText() }.orEmpty()
    }
}
