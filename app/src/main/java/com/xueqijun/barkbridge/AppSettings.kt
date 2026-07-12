package com.xueqijun.barkbridge

import android.content.Context

object AppSettings {
    private const val DEFAULT_SERVER = "https://api.day.app"
    private const val DEFAULT_BLOCK = "广告,拼多多,淘宝"
    private const val DEFAULT_IMPORTANT = "验证码,银行,转账,老板"

    fun appEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "app_enabled", true)
    fun setAppEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "app_enabled", value)

    fun wechatEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "wechat_enabled", true)
    fun setWechatEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "wechat_enabled", value)

    fun callEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "call_enabled", true)
    fun setCallEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "call_enabled", value)

    fun quietHoursEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "quiet_hours_enabled")
    fun setQuietHoursEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "quiet_hours_enabled", value)

    fun quietStart(ctx: Context): String = Prefs.get(ctx, "quiet_start").ifBlank { "23:00" }
    fun setQuietStart(ctx: Context, value: String) = Prefs.set(ctx, "quiet_start", value.trim().ifBlank { "23:00" })

    fun quietEnd(ctx: Context): String = Prefs.get(ctx, "quiet_end").ifBlank { "08:00" }
    fun setQuietEnd(ctx: Context, value: String) = Prefs.set(ctx, "quiet_end", value.trim().ifBlank { "08:00" })

    fun allowImportantInQuiet(ctx: Context): Boolean = Prefs.getBool(ctx, "quiet_allow_important", true)
    fun setAllowImportantInQuiet(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "quiet_allow_important", value)

    fun allowCallsInQuiet(ctx: Context): Boolean = Prefs.getBool(ctx, "quiet_allow_calls", true)
    fun setAllowCallsInQuiet(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "quiet_allow_calls", value)

    fun logFilter(ctx: Context): String = Prefs.get(ctx, "log_filter").ifBlank { "全部" }
    fun setLogFilter(ctx: Context, value: String) = Prefs.set(ctx, "log_filter", value.ifBlank { "全部" })

    fun barkKey(ctx: Context): String = Prefs.get(ctx, "key").trim()
    fun setBarkKey(ctx: Context, value: String) = Prefs.set(ctx, "key", value.trim())

    fun barkServer(ctx: Context): String = Prefs.get(ctx, "bark_server").ifBlank { DEFAULT_SERVER }
    fun setBarkServer(ctx: Context, value: String) = Prefs.set(ctx, "bark_server", value.trim().ifBlank { DEFAULT_SERVER })

    fun barkGroup(ctx: Context): String = Prefs.get(ctx, "bark_group").ifBlank { "BarkBridge" }
    fun setBarkGroup(ctx: Context, value: String) = Prefs.set(ctx, "bark_group", value.trim())

    fun barkSound(ctx: Context): String = Prefs.get(ctx, "bark_sound").trim()
    fun setBarkSound(ctx: Context, value: String) = Prefs.set(ctx, "bark_sound", value.trim())

    fun barkIcon(ctx: Context): String = Prefs.get(ctx, "bark_icon").trim()
    fun setBarkIcon(ctx: Context, value: String) = Prefs.set(ctx, "bark_icon", value.trim())

    fun barkLevel(ctx: Context): String = Prefs.get(ctx, "bark_level").ifBlank { "active" }
    fun setBarkLevel(ctx: Context, value: String) = Prefs.set(ctx, "bark_level", value.trim().ifBlank { "active" })

    fun diagnosticLogs(ctx: Context): Boolean = Prefs.getBool(ctx, "diagnostic_logs")
    fun setDiagnosticLogs(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "diagnostic_logs", value)

    fun maskPhoneInLogs(ctx: Context): Boolean = Prefs.getBool(ctx, "mask_phone_logs", true)
    fun setMaskPhoneInLogs(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "mask_phone_logs", value)

    fun saveMessageBody(ctx: Context): Boolean = Prefs.getBool(ctx, "save_message_body", true)
    fun setSaveMessageBody(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "save_message_body", value)

    fun blockGroupChats(ctx: Context): Boolean = Prefs.getBool(ctx, "block_group_chats")
    fun setBlockGroupChats(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "block_group_chats", value)

    fun blockKeywords(ctx: Context): String = Prefs.get(ctx, "block_keywords").ifBlank { DEFAULT_BLOCK }
    fun setBlockKeywords(ctx: Context, value: String) = Prefs.set(ctx, "block_keywords", value.trim())

    fun importantKeywords(ctx: Context): String = Prefs.get(ctx, "important_keywords").ifBlank { DEFAULT_IMPORTANT }
    fun setImportantKeywords(ctx: Context, value: String) = Prefs.set(ctx, "important_keywords", value.trim())

    fun allowedContacts(ctx: Context): String = Prefs.get(ctx, "allowed_contacts").trim()
    fun setAllowedContacts(ctx: Context, value: String) = Prefs.set(ctx, "allowed_contacts", value.trim())

    fun keywordList(value: String): List<String> {
        return value.split(",", "，", "\n")
            .map { it.trim() }
            .filter { it.isNotBlank() }
    }
}
