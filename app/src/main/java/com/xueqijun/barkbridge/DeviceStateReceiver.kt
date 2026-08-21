package com.xueqijun.barkbridge

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class DeviceStateReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return
        LogStore.add(context, "设备状态: $action", diagnostic = true)
        BatteryEvents.handle(context, intent)
        BridgeForegroundService.start(context)
        PendingPushes.flush(context, action)
        PendingConversationUploads.flush(context, action)
    }
}
