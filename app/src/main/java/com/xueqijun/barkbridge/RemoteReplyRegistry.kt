package com.xueqijun.barkbridge

import android.app.Notification
import android.app.PendingIntent
import android.app.RemoteInput
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.service.notification.StatusBarNotification
import java.net.URLEncoder
import java.security.SecureRandom
import java.util.concurrent.ConcurrentHashMap

object RemoteReplyRegistry {
    private const val TTL_MS = 30 * 60 * 1000L
    private val random = SecureRandom()
    private val entries = ConcurrentHashMap<String, Entry>()

    data class Entry(
        val token: String,
        val contact: String,
        val action: Notification.Action,
        val remoteInputs: Array<RemoteInput>,
        val createdAt: Long
    )

    fun capture(ctx: Context, sbn: StatusBarNotification, contact: String, text: String): String? {
        if (!AppSettings.remoteReplyEnabled(ctx)) return null
        val pageUrl = AppSettings.remoteReplyPageUrl(ctx)
        if (pageUrl.isBlank()) {
            LogStore.add(ctx, "远程回复未生成: 缺少 iPhone 回复页面 URL", category = "回复")
            return null
        }

        if (AppSettings.remoteReplyTarget(ctx) == "mac") {
            if (!allowedMacContact(ctx, contact)) {
                LogStore.add(ctx, "远程回复未生成: 联系人未命中 Mac 回复白名单 $contact", category = "回复")
                return null
            }
            val token = newToken()
            LogStore.add(ctx, "已生成 Mac 回复令牌: $contact", diagnostic = true, category = "回复")
            return buildReplyUrl(pageUrl, token, contact, text)
        }

        if (!allowedAndroidContact(ctx, contact)) return null
        val action = firstReplyAction(sbn.notification) ?: run {
            LogStore.add(ctx, "微信通知没有快捷回复动作，无法生成远程回复链接", diagnostic = true, category = "回复")
            return null
        }
        val inputs = action.remoteInputs ?: return null
        prune()

        val token = newToken()
        entries[token] = Entry(
            token = token,
            contact = contact,
            action = action,
            remoteInputs = inputs,
            createdAt = System.currentTimeMillis()
        )
        LogStore.add(ctx, "已生成远程回复令牌: $contact", diagnostic = true, category = "回复")
        return buildReplyUrl(pageUrl, token, contact, text)
    }

    fun send(ctx: Context, token: String, replyText: String): Boolean {
        prune()
        val entry = entries[token] ?: run {
            LogStore.add(ctx, "远程回复失败: 令牌不存在或已过期", category = "回复")
            return false
        }
        if (replyText.isBlank()) {
            LogStore.add(ctx, "远程回复失败: 回复内容为空", category = "回复")
            return false
        }

        return try {
            val intent = Intent()
            val results = Bundle()
            for (input in entry.remoteInputs) {
                results.putCharSequence(input.resultKey, replyText)
            }
            RemoteInput.addResultsToIntent(entry.remoteInputs, intent, results)
            entry.action.actionIntent.send(ctx, 0, intent)
            entries.remove(token)
            LogStore.add(ctx, "远程回复已发送: ${entry.contact}", category = "回复")
            true
        } catch (e: PendingIntent.CanceledException) {
            entries.remove(token)
            LogStore.add(ctx, "远程回复失败: 微信通知已失效", category = "回复")
            false
        } catch (e: Exception) {
            LogStore.add(ctx, "远程回复失败: ${e.javaClass.simpleName} ${e.message.orEmpty()}".take(180), category = "回复")
            false
        }
    }

    private fun firstReplyAction(notification: Notification): Notification.Action? {
        return notification.actions?.firstOrNull { action ->
            action.actionIntent != null && action.remoteInputs?.isNotEmpty() == true
        }
    }

    private fun allowedMacContact(ctx: Context, contact: String): Boolean {
        val configured = AppSettings.remoteReplyContacts(ctx)
        val keywords = AppSettings.keywordList(configured)
        if (keywords.isEmpty()) return true
        return keywords.any { contact.contains(it, ignoreCase = true) }
    }

    private fun allowedAndroidContact(ctx: Context, contact: String): Boolean {
        val configured = AppSettings.remoteReplyContacts(ctx).ifBlank { AppSettings.allowedContacts(ctx) }
        val keywords = AppSettings.keywordList(configured)
        if (keywords.isEmpty()) return false
        return keywords.any { contact.contains(it, ignoreCase = true) }
    }

    private fun prune() {
        val now = System.currentTimeMillis()
        entries.entries.removeIf { now - it.value.createdAt > TTL_MS }
    }

    private fun newToken(): String {
        val bytes = ByteArray(16)
        random.nextBytes(bytes)
        return bytes.joinToString("") { "%02x".format(it) }
    }

    private fun buildReplyUrl(base: String, token: String, contact: String, text: String): String {
        val separator = if (base.contains("?")) "&" else "?"
        return base + separator +
            "token=${encode(token)}" +
            "&contact=${encode(contact)}" +
            "&message=${encode(text.take(180))}"
    }

    private fun encode(value: String): String {
        return URLEncoder.encode(value, "UTF-8").replace("+", "%20")
    }
}
