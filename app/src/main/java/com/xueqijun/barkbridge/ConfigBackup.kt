package com.xueqijun.barkbridge

import android.content.Context
import org.json.JSONObject

object ConfigBackup {
    private val keys = listOf(
        "app_enabled", "wechat_enabled", "call_enabled",
        "missed_call_enabled", "sms_notification_enabled", "general_notification_enabled",
        "general_notification_packages", "battery_notification_enabled", "low_battery_threshold",
        "remote_reply_enabled", "remote_reply_target", "remote_reply_contacts", "remote_reply_page_url",
        "remote_reply_poll_url", "remote_reply_poll_seconds",
        "quiet_hours_enabled", "quiet_start", "quiet_end", "quiet_allow_important", "quiet_allow_calls",
        "key", "bark_server", "bark_group", "bark_sound", "bark_icon", "bark_level",
        "diagnostic_logs", "mask_phone_logs", "save_message_body",
        "block_group_chats", "block_keywords", "important_keywords", "allowed_contacts"
    )

    fun export(ctx: Context): String {
        val sp = ctx.getSharedPreferences("bark_bridge_v1", 0)
        val json = JSONObject()
        json.put("version", 1)
        for (key in keys) {
            if (!sp.contains(key)) continue
            when (val value = sp.all[key]) {
                is Boolean -> json.put(key, value)
                is String -> json.put(key, value)
            }
        }
        return json.toString(2)
    }

    fun import(ctx: Context, raw: String): Boolean {
        return try {
            val json = JSONObject(raw)
            val sp = ctx.getSharedPreferences("bark_bridge_v1", 0)
            val edit = sp.edit()
            for (key in keys) {
                if (!json.has(key)) continue
                when (val value = json.get(key)) {
                    is Boolean -> edit.putBoolean(key, value)
                    is String -> edit.putString(key, value)
                }
            }
            edit.apply()
            true
        } catch (e: Exception) {
            false
        }
    }
}
