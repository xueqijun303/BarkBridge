package com.example.barkbridge

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.net.Uri
import android.provider.ContactsContract

object ContactNames {
    fun displayFor(ctx: Context, number: String): String {
        if (number.isBlank() || number == "未知号码") return number
        val name = lookup(ctx, number)
        return if (name.isNullOrBlank()) number else "$name $number"
    }

    private fun lookup(ctx: Context, number: String): String? {
        if (ctx.checkSelfPermission(Manifest.permission.READ_CONTACTS) != PackageManager.PERMISSION_GRANTED) {
            return null
        }
        val uri = Uri.withAppendedPath(
            ContactsContract.PhoneLookup.CONTENT_FILTER_URI,
            Uri.encode(number)
        )
        val projection = arrayOf(ContactsContract.PhoneLookup.DISPLAY_NAME)
        return try {
            ctx.contentResolver.query(uri, projection, null, null, null)?.use { cursor ->
                if (cursor.moveToFirst()) cursor.getString(0) else null
            }
        } catch (e: Exception) {
            LogStore.add(ctx, "联系人匹配失败: ${e.javaClass.simpleName}")
            null
        }
    }
}
