
package com.xueqijun.barkbridge

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.telephony.TelephonyManager
import android.telephony.PhoneStateListener

class CallService(val ctx:Context){

    private var listener: PhoneStateListener? = null

    fun start(){
        if(listener != null) return
        if(!hasPermission(Manifest.permission.READ_PHONE_STATE)){
            LogStore.add(ctx, "来电监听未启动: 缺少 READ_PHONE_STATE")
            return
        }
        try{
            val tm = ctx.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager

            val newListener = object:PhoneStateListener(){
                override fun onCallStateChanged(state:Int,phoneNumber:String?){
                    if(state==TelephonyManager.CALL_STATE_RINGING){
                        val number = if(hasCallNumberPermission()) phoneNumber ?: "未知号码" else "未知号码"
                        CallEvents.notifyIncoming(ctx, number, "监听")
                    }
                }
            }
            tm.listen(newListener,PhoneStateListener.LISTEN_CALL_STATE)
            listener = newListener
            LogStore.add(ctx, "来电监听已启动")
        }catch(e:SecurityException){
            LogStore.add(ctx, "来电监听启动失败: ${e.message ?: "权限不足"}")
        }
    }

    fun stop(){
        val activeListener = listener ?: return
        try{
            val tm = ctx.getSystemService(Context.TELEPHONY_SERVICE) as TelephonyManager
            tm.listen(activeListener, PhoneStateListener.LISTEN_NONE)
        }catch(e:Exception){
            LogStore.add(ctx, "来电监听停止失败")
        }finally{
            listener = null
        }
    }

    private fun hasCallNumberPermission(): Boolean {
        return hasPermission(Manifest.permission.READ_CALL_LOG) ||
            hasPermission(Manifest.permission.READ_PHONE_NUMBERS)
    }

    private fun hasPermission(permission: String): Boolean {
        return ctx.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED
    }
}
