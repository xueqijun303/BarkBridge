
package com.example.barkbridge

object RuleEngine {

    val blockWords = mutableListOf("广告","拼多多","淘宝")
    val importantWords = mutableListOf("验证码","银行","转账","老板")

    fun shouldDrop(text:String):Boolean{
        return blockWords.any{ text.contains(it) }
    }

    fun isImportant(text:String):Boolean{
        return importantWords.any{ text.contains(it) }
    }
}
