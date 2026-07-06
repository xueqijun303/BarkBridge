
package com.xueqijun.barkbridge

import android.content.Context

object LogStore {
    private const val KEY="logs"

    fun add(ctx:Context,v:String){
        val old = get(ctx)
        Prefs.set(ctx,KEY, (v+"\n"+old).take(5000))
    }

    fun get(ctx:Context):String{
        return Prefs.get(ctx,KEY)
    }

    fun clear(ctx:Context){
        Prefs.set(ctx,KEY,"")
    }
}
