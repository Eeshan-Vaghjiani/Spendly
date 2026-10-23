package com.evagh.capstone.spending_support.mpesa

import java.math.BigDecimal
import java.text.ParsePosition
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

enum class MpesaKind { SENT, RECEIVED, AIRTIME, TILL, PAYBILL, WITHDRAWAL, DEPOSIT, PAYMENT, REVERSAL }

data class MpesaParsedEvent(
    val transactionCode: String,
    val timestamp: String,
    val kind: MpesaKind,
    val direction: String,
    val principalAmount: String,
    val transactionFee: String,
    val category: String,
    val merchant: String?,
    val originalReference: String? = null,
    val feeRefundAmount: String = "0.00",
) {
    // This allowlist is the entire persisted/uploaded event: no raw message,
    // balance, phone number, bill account, URL or device SMS identifier.
    fun normalized(): Map<String, Any?> {
        val common = mutableMapOf<String, Any?>(
            "external_reference" to transactionCode, "transaction_timestamp" to timestamp,
            "kind" to kind.name.lowercase(Locale.ROOT), "parser_version" to "mpesa-v1",
            "amount" to principalAmount,
        )
        if (kind == MpesaKind.REVERSAL) {
            common["original_reference"] = originalReference
            common["original_transaction_type"] = direction
            common["fee_refund_amount"] = feeRefundAmount
        } else {
            common.putAll(mapOf("transaction_type" to direction, "transaction_cost" to transactionFee,
                "category" to category, "merchant" to merchant))
        }
        return common
    }
}

sealed class MpesaParseResult {
    data class Parsed(val event: MpesaParsedEvent) : MpesaParseResult()
    data object Unsupported : MpesaParseResult()
    data object Invalid : MpesaParseResult()
}

/** Bounded, typed confirmation families. SMS matching is not authenticity proof. */
class MpesaSmsParser {
    companion object {
        const val MAX_BODY = 4096
        fun allowedSender(sender: String?): Boolean = sender?.trim()?.uppercase(Locale.ROOT) in setOf("MPESA", "M-PESA")
        private const val MONEY = "((?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\\.[0-9]{1,2})?)"
        private const val CURRENCY = "Ksh\\s*"
        private val PREFIX = Regex("^([A-Z0-9]{10})\\s+confirmed\\s*[.!]?\\s*(.+)$", RegexOption.IGNORE_CASE)
        private val DATE = Regex("\\bon (\\d{1,2})/(\\d{1,2})/(\\d{4}|\\d{2}) at (\\d{1,2}):(\\d{2})\\s*(AM|PM)\\b", RegexOption.IGNORE_CASE)
        private val FAILED = Regex("\\b(failed|insufficient|unsuccessful|cancelled|pending|requested|OTP)\\b", RegexOption.IGNORE_CASE)
        private val FEE = Regex("Transaction (?:cost|fee)[,.:]?\\s*" + CURRENCY + MONEY + "(?=\\s|,(?![0-9])|\\.(?:\\s|$)|$)", RegexOption.IGNORE_CASE)
        private val FEE_REFUND = Regex("Transaction fee refunded[,.:]?\\s*" + CURRENCY + MONEY + "(?=\\s|,(?![0-9])|\\.(?:\\s|$)|$)", RegexOption.IGNORE_CASE)
    }

    private data class Family(val kind: MpesaKind, val expression: Regex, val hasCounterparty: Boolean = true)
    private fun family(kind: MpesaKind, prefix: String, counterparty: Boolean = true) =
        Family(kind, Regex(prefix, RegexOption.IGNORE_CASE), counterparty)
    private val families = listOf(
        family(MpesaKind.AIRTIME, "^You bought " + CURRENCY + MONEY + " of airtime on ", false),
        family(MpesaKind.RECEIVED, "^You have received " + CURRENCY + MONEY + " from (.{1,180}?) on "),
        family(MpesaKind.PAYBILL, "^" + CURRENCY + MONEY + " sent to (.{1,120}?) for account .{1,80}? on "),
        family(MpesaKind.SENT, "^" + CURRENCY + MONEY + " sent to (.{1,180}?) on "),
        family(MpesaKind.TILL, "^" + CURRENCY + MONEY + " paid to (.{1,180}?)\\.? on "),
        family(MpesaKind.WITHDRAWAL, "^(?:You have withdrawn |" + "(?=" + CURRENCY + "))" + CURRENCY + MONEY + "(?: withdrawn)? from (.{1,180}?) on "),
        family(MpesaKind.DEPOSIT, "^" + CURRENCY + MONEY + " deposited (?:to|into) your (?:M-PESA )?account on ", false),
    )
    private val reversal = Regex("^" + CURRENCY + MONEY + " from transaction ([A-Z0-9]{10}) has been reversed (back into|from) your (?:M-PESA )?account on ", RegexOption.IGNORE_CASE)

    fun parse(sender: String?, body: String): MpesaParseResult {
        if (!allowedSender(sender)) return MpesaParseResult.Unsupported
        if (body.length > MAX_BODY) return MpesaParseResult.Invalid
        val text = body.replace('\u00a0', ' ').replace(Regex("[\\t\\r\\n ]+"), " ").trim()
        val prefix = PREFIX.matchEntire(text) ?: return MpesaParseResult.Unsupported
        if (!prefix.groupValues[1].all { it in 'a'..'z' || it in 'A'..'Z' || it in '0'..'9' }) return MpesaParseResult.Invalid
        val reference = prefix.groupValues[1].uppercase(Locale.ROOT)
        val content = prefix.groupValues[2]
        if (FAILED.containsMatchIn(content)) return MpesaParseResult.Unsupported
        val time = timestamp(content) ?: return MpesaParseResult.Invalid
        val reversed = reversal.find(content)
        if (reversed != null) {
            if (DATE.find(content)?.range?.first != reversed.range.last - 2) return MpesaParseResult.Invalid
            val original = reversed.groupValues[2].uppercase(Locale.ROOT)
            if (original == reference) return MpesaParseResult.Invalid
            val amount = money(reversed.groupValues[1], false) ?: return MpesaParseResult.Invalid
            val refunds = FEE_REFUND.findAll(content).toList()
            if (content.contains("Transaction fee refunded", true) && refunds.isEmpty()) return MpesaParseResult.Invalid
            if (refunds.size > 1) return MpesaParseResult.Invalid
            val refund = refunds.firstOrNull()?.let { money(it.groupValues[1], true) ?: return MpesaParseResult.Invalid } ?: "0.00"
            return MpesaParseResult.Parsed(MpesaParsedEvent(reference, time, MpesaKind.REVERSAL,
                if (reversed.groupValues[3].equals("back into", true)) "expense" else "income",
                amount, "0.00", "transfers", null, original, refund))
        }
        if (Regex("\\brevers", RegexOption.IGNORE_CASE).containsMatchIn(content)) return MpesaParseResult.Unsupported
        for (family in families) {
            val matched = family.expression.find(content) ?: continue
            if (DATE.find(content)?.range?.first != matched.range.last - 2) return MpesaParseResult.Invalid
            val amount = money(matched.groupValues[1], false) ?: return MpesaParseResult.Invalid
            val fees = FEE.findAll(content).toList()
            if (Regex("Transaction (?:cost|fee)", RegexOption.IGNORE_CASE).containsMatchIn(content) && fees.isEmpty()) return MpesaParseResult.Invalid
            if (fees.size > 1) return MpesaParseResult.Invalid
            val fee = fees.firstOrNull()?.let { money(it.groupValues[1], true) ?: return MpesaParseResult.Invalid } ?: "0.00"
            val direction = if (family.kind in setOf(MpesaKind.RECEIVED, MpesaKind.DEPOSIT)) "income" else "expense"
            if (direction == "income" && fee != "0.00") return MpesaParseResult.Invalid
            val merchant = if (family.hasCounterparty) counterparty(matched.groupValues[2]) else
                if (family.kind == MpesaKind.AIRTIME) "M-PESA Airtime" else "Cash deposit"
            return MpesaParseResult.Parsed(MpesaParsedEvent(reference, time, family.kind, direction,
                amount, fee, category(family.kind, merchant), merchant))
        }
        return MpesaParseResult.Unsupported
    }

    private fun money(value: String, allowZero: Boolean): String? = try {
        if (value.length > 20) null else {
            val amount = BigDecimal(value.replace(",", ""))
            if (amount.scale() > 2 || amount < BigDecimal.ZERO || (!allowZero && amount.signum() == 0) ||
                amount > BigDecimal("999999999999.99")) null else amount.setScale(2).toPlainString()
        }
    } catch (_: NumberFormatException) { null }

    private fun timestamp(content: String): String? {
        val matched = DATE.find(content) ?: return null
        val (day, month, rawYear, hour, minute, half) = matched.destructured
        val year = if (rawYear.length == 2) "20$rawYear" else rawYear
        if (year.toInt() !in 2000..2099 || hour.toInt() !in 1..12) return null
        val input = "$day/$month/$year $hour:$minute ${half.uppercase(Locale.ROOT)}"
        val parser = SimpleDateFormat("d/M/yyyy h:mm a", Locale.US).apply {
            isLenient = false; timeZone = TimeZone.getTimeZone("Africa/Nairobi")
        }
        val position = ParsePosition(0)
        val date = parser.parse(input, position) ?: return null
        if (position.index != input.length) return null
        return SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }.format(date)
    }

    private fun counterparty(value: String): String? = value
        .replace(Regex("(?:^|\\s)(?:\\+?254|0)[0-9*]{8,12}(?=\\s|$|\\.)"), " ")
        .replace(Regex("\\s+for account\\b.*", RegexOption.IGNORE_CASE), "")
        .trim().trimEnd('.').take(120).takeIf { it.isNotBlank() }

    private fun category(kind: MpesaKind, merchant: String?): String {
        if (kind == MpesaKind.AIRTIME) return "airtime_and_data"
        if (kind in setOf(MpesaKind.SENT, MpesaKind.DEPOSIT, MpesaKind.WITHDRAWAL)) return "transfers"
        if (kind == MpesaKind.RECEIVED) return "other"
        return when (merchant?.uppercase(Locale.ROOT)) {
            "NAIVAS", "QUICKMART", "CARREFOUR" -> "food"
            "KENYA POWER", "KPLC PREPAID", "NAIROBI WATER" -> "utilities"
            "NETFLIX", "SPOTIFY" -> "subscriptions"
            else -> "other"
        }
    }
}
