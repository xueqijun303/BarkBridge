
package com.xueqijun.barkbridge

import android.content.Context

object Prefs {
    private const val SP = "bark_bridge_v1"

    fun set(ctx: Context, k: String, v: String) {
        ctx.getSharedPreferences(SP,0).edit().putString(k,v).apply()
    }

    fun get(ctx: Context, k: String): String {
        return ctx.getSharedPreferences(SP,0).getString(k,"") ?: ""
    }

    fun setBool(ctx: Context, k: String, v: Boolean){
        ctx.getSharedPreferences(SP,0).edit().putBoolean(k,v).apply()
    }

    fun getBool(ctx: Context, k: String, defaultValue: Boolean = false): Boolean {
        return ctx.getSharedPreferences(SP,0).getBoolean(k,defaultValue)
    }
}
