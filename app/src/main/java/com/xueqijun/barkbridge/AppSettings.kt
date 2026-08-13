package com.xueqijun.barkbridge

import android.content.Context

object AppSettings {
    private const val DEFAULT_SERVER = "https://api.day.app"
    private const val DEFAULT_BLOCK = "广告,拼多多,淘宝"
    private const val DEFAULT_IMPORTANT = "验证码,银行,转账,老板"
    private const val DEFAULT_REPLY_PAGE = "https://barkbridge-relay.xueqijun303.workers.dev/reply"
    private const val DEFAULT_CHAT_INGEST = "https://barkbridge-relay.xueqijun303.workers.dev/ingest"
    private const val DEFAULT_CHAT_PAGE = "https://barkbridge-relay.xueqijun303.workers.dev/chat"

    fun appEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "app_enabled", true)
    fun setAppEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "app_enabled", value)

    fun wechatEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "wechat_enabled", true)
    fun setWechatEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "wechat_enabled", value)

    fun callEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "call_enabled", true)
    fun setCallEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "call_enabled", value)

    fun missedCallEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "missed_call_enabled", true)
    fun setMissedCallEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "missed_call_enabled", value)

    fun smsNotificationEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "sms_notification_enabled", true)
    fun setSmsNotificationEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "sms_notification_enabled", value)

    fun generalNotificationEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "general_notification_enabled")
    fun setGeneralNotificationEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "general_notification_enabled", value)

    fun generalNotificationPackages(ctx: Context): String = Prefs.get(ctx, "general_notification_packages")
        .ifBlank { "com.tencent.mobileqq,com.alibaba.android.rimet,com.ss.android.lark,com.ss.android.lark.kami,com.eg.android.AlipayGphone,com.google.android.gm" }
    fun setGeneralNotificationPackages(ctx: Context, value: String) = Prefs.set(ctx, "general_notification_packages", value.trim())

    fun batteryNotificationEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "battery_notification_enabled", true)
    fun setBatteryNotificationEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "battery_notification_enabled", value)

    fun lowBatteryThreshold(ctx: Context): String = Prefs.get(ctx, "low_battery_threshold").ifBlank { "20" }
    fun setLowBatteryThreshold(ctx: Context, value: String) = Prefs.set(ctx, "low_battery_threshold", value.trim().ifBlank { "20" })

    fun remoteReplyEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "remote_reply_enabled", true)
    fun setRemoteReplyEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "remote_reply_enabled", value)

    fun remoteReplyTarget(ctx: Context): String = Prefs.get(ctx, "remote_reply_target").ifBlank { "mac" }
    fun setRemoteReplyTarget(ctx: Context, value: String) = Prefs.set(ctx, "remote_reply_target", value.trim().ifBlank { "mac" })

    fun remoteReplyContacts(ctx: Context): String = Prefs.get(ctx, "remote_reply_contacts").trim()
    fun setRemoteReplyContacts(ctx: Context, value: String) = Prefs.set(ctx, "remote_reply_contacts", value.trim())

    fun remoteReplyPageUrl(ctx: Context): String = Prefs.get(ctx, "remote_reply_page_url").ifBlank { DEFAULT_REPLY_PAGE }.trim()
    fun setRemoteReplyPageUrl(ctx: Context, value: String) = Prefs.set(ctx, "remote_reply_page_url", value.trim())

    fun remoteReplyPollUrl(ctx: Context): String = Prefs.get(ctx, "remote_reply_poll_url").trim()
    fun setRemoteReplyPollUrl(ctx: Context, value: String) = Prefs.set(ctx, "remote_reply_poll_url", value.trim())

    fun remoteReplyPollSeconds(ctx: Context): String = Prefs.get(ctx, "remote_reply_poll_seconds").ifBlank { "20" }
    fun setRemoteReplyPollSeconds(ctx: Context, value: String) = Prefs.set(ctx, "remote_reply_poll_seconds", value.trim().ifBlank { "20" })

    fun conversationMirrorEnabled(ctx: Context): Boolean = Prefs.getBool(ctx, "conversation_mirror_enabled", true)
    fun setConversationMirrorEnabled(ctx: Context, value: Boolean) = Prefs.setBool(ctx, "conversation_mirror_enabled", value)

    fun conversationIngestUrl(ctx: Context): String = Prefs.get(ctx, "conversation_ingest_url").ifBlank { DEFAULT_CHAT_INGEST }.trim()
    fun setConversationIngestUrl(ctx: Context, value: String) = Prefs.set(ctx, "conversation_ingest_url", value.trim())

    fun conversationChatPageUrl(ctx: Context): String = Prefs.get(ctx, "conversation_chat_page_url").ifBlank { DEFAULT_CHAT_PAGE }.trim()
    fun setConversationChatPageUrl(ctx: Context, value: String) = Prefs.set(ctx, "conversation_chat_page_url", value.trim())

    fun conversationRelaySecret(ctx: Context): String = Prefs.get(ctx, "conversation_relay_secret").trim()
    fun setConversationRelaySecret(ctx: Context, value: String) = Prefs.set(ctx, "conversation_relay_secret", value.trim())

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
