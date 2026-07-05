
package com.example.barkbridge

object AI {
    fun summary(text:String):String{
        if(text.length<=40) return text
        return text.take(40) + "..."
    }
}
