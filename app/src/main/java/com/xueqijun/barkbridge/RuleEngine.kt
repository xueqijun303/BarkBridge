
package com.xueqijun.barkbridge

import android.content.Context

object RuleEngine {

    fun shouldDrop(ctx: Context, title: String, text: String): Boolean {
        val full = "$title $text"
        if (AppSettings.blockGroupChats(ctx) && isLikelyGroupChat(title, text)) return true
        val allowed = AppSettings.keywordList(AppSettings.allowedContacts(ctx))
        if (allowed.isNotEmpty() && allowed.none { full.contains(it, ignoreCase = true) }) return true
        return AppSettings.keywordList(AppSettings.blockKeywords(ctx))
            .any { full.contains(it, ignoreCase = true) }
    }

    fun isImportant(ctx: Context, text:String):Boolean{
        return AppSettings.keywordList(AppSettings.importantKeywords(ctx))
            .any{ text.contains(it, ignoreCase = true) }
    }

    private fun isLikelyGroupChat(title: String, text: String): Boolean {
        return (title.contains("[") && title.contains("条]")) || text.contains(":")
    }
}
