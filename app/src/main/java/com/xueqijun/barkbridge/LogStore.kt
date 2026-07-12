
package com.xueqijun.barkbridge

import android.content.Context
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object LogStore {
    private const val KEY="logs"
    private const val MAX_LENGTH = 12000
    private val phoneRegex = Regex("""(?<!\d)(\d{3})\d{4}(\d{4})(?!\d)""")

    fun add(ctx:Context,v:String, diagnostic: Boolean = false, category: String = "系统"){
        if (diagnostic && !AppSettings.diagnosticLogs(ctx)) return
        val old = get(ctx)
        val line = "${timestamp()} [$category] ${sanitize(ctx, v)}"
        Prefs.set(ctx,KEY, (line+"\n"+old).take(MAX_LENGTH))
    }

    fun get(ctx:Context):String{
        return Prefs.get(ctx,KEY)
    }

    fun getFiltered(ctx: Context): String {
        val filter = AppSettings.logFilter(ctx)
        val raw = get(ctx)
        if (filter == "全部" || raw.isBlank()) return raw
        return raw.lineSequence()
            .filter { it.contains("[$filter]") }
            .joinToString("\n")
    }

    fun clear(ctx:Context){
        Prefs.set(ctx,KEY,"")
    }

    fun sanitize(ctx: Context, value: String): String {
        if (!AppSettings.maskPhoneInLogs(ctx)) return value
        return phoneRegex.replace(value, "$1****$2")
    }

    private fun timestamp(): String {
        return SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
    }
}
