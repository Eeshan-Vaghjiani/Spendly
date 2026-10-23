package com.evagh.capstone.spending_support.mpesa

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony

class MpesaSmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION || !MpesaImporter.mayReceive(context)) return
        // Gate before asking the platform to decode PDUs. Acceptance packages
        // always return above: a personal phone can never become a test inbox.
        val pending = goAsync()
        MpesaImporter.receiverExecutor.execute {
            try {
                MpesaImporter.withReceiveGate(context) {
                    val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
                    if (messages.size > 30) return@withReceiveGate
                    val sender = messages.firstOrNull()?.originatingAddress ?: return@withReceiveGate
                    if (!MpesaSmsParser.allowedSender(sender) || messages.any { it.originatingAddress != sender }) return@withReceiveGate
                    val body = StringBuilder()
                    for (message in messages) {
                        body.append(message.messageBody)
                        if (body.length > MpesaSmsParser.MAX_BODY) return@withReceiveGate
                    }
                    MpesaImporter.receive(context, sender, body.toString())
                }
            } catch (_: Exception) {
                // No SMS, account identifiers or credentials in diagnostics.
            } finally { pending.finish() }
        }
    }
}
