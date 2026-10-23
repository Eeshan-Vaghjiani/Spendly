package com.evagh.capstone.spending_support.mpesa

import org.junit.Assert.*
import org.junit.Test

class MpesaSmsParserTest {
    private val parser = MpesaSmsParser()
    private fun text(content: String) = "TEST000001 Confirmed.$content on 11/10/26 at 7:39 PM. New M-PESA balance is Ksh9,876.54. Amount you can transact within the day is 456,789.00."
    private fun parsed(content: String): MpesaParsedEvent =
        (parser.parse("MPESA", text(content)) as MpesaParseResult.Parsed).event

    @Test fun sentKeepsPrincipalSeparateFromFeeAndPrivateMetadata() {
        val value = parser.parse("M-PESA", text("Ksh214.25 sent to Example Person 0700000001") + " Transaction cost, Ksh8.50.") as MpesaParseResult.Parsed
        assertEquals("214.25", value.event.principalAmount)
        assertEquals("8.50", value.event.transactionFee)
        assertEquals("Example Person", value.event.merchant)
        assertEquals("transfers", value.event.category)
        assertEquals("2026-10-11T16:39:00Z", value.event.timestamp)
        assertFalse(value.event.normalized().toString().contains("9,876"))
        assertFalse(value.event.normalized().toString().contains("0700000001"))
    }

    @Test fun receivedMaskedPhoneCommasAndWhitespace() {
        val value = parsed("You have received Ksh 2,345.60 from Fictional Sender 0700***002")
        assertEquals("income", value.direction)
        assertEquals("2345.60", value.principalAmount)
        assertEquals("Fictional Sender", value.merchant)
    }

    @Test fun airtimeZeroFeeNeverBecomesBalance() {
        val value = parsed("You bought Ksh75.00 of airtime")
        assertEquals(MpesaKind.AIRTIME, value.kind)
        assertEquals("airtime_and_data", value.category)
        assertEquals("0.00", value.transactionFee)
    }

    @Test fun merchantFamiliesAndNeutralCategories() {
        assertEquals("food", parsed("Ksh120.00 paid to NAIVAS").category)
        assertEquals(MpesaKind.PAYBILL, parsed("Ksh120.00 sent to KENYA POWER for account 998877").kind)
        assertEquals("utilities", parsed("Ksh120.00 sent to KENYA POWER for account 998877").category)
        assertFalse(parsed("Ksh120.00 sent to KENYA POWER for account 998877").normalized().toString().contains("998877"))
        assertEquals("other", parsed("Ksh120.00 paid to Unrecognized shop").category)
        assertEquals(MpesaKind.WITHDRAWAL, parsed("Ksh120.00 withdrawn from Fictional agent").kind)
        assertEquals(MpesaKind.DEPOSIT, parsed("Ksh120.00 deposited into your M-PESA account").kind)
    }

    @Test fun malformedAndNonfinancialMessagesNeverBecomeTransactions() {
        for (body in listOf("Win Ksh1000!", "Your balance is Ksh100.00", "Insufficient funds.",
            "TEST000001 Confirmed. Your payment failed. Ksh120.00", "Your OTP is 123456",
            text("Ksh120.00 purchased a mystery product"), "Fuliza promotion Ksh100")) {
            assertFalse(parser.parse("MPESA", body) is MpesaParseResult.Parsed)
        }
        assertSame(MpesaParseResult.Unsupported, parser.parse("0700000001", text("Ksh120.00 paid to Example")))
        assertSame(MpesaParseResult.Invalid, parser.parse("MPESA", "x".repeat(4097)))
        assertSame(MpesaParseResult.Invalid, parser.parse("MPESA", text("Ksh0.00 paid to Example")))
        assertFalse(parser.parse("MPESA", text("Ksh1.001 paid to Example")) is MpesaParseResult.Parsed)
        assertSame(MpesaParseResult.Invalid, parser.parse("MPESA", text("Ksh120.00 paid to Example").replace("11/10/26", "31/02/26")))
    }

    @Test fun referenceStableAcrossRepeatedDeliveryAndCaseAndSpacing() {
        val body = text("Ksh120.00 sent to Example")
        val first = parser.parse("MPESA", body) as MpesaParseResult.Parsed
        assertEquals(first, parser.parse(" mpesa ", body.replace("Confirmed.", "confirmed.\n")))
        assertTrue(first.event.transactionCode.length == 10)
    }

    @Test fun reversalRequiresCompletedDirectionAndOriginalReference() {
        val result = parsed("Ksh214.25 from transaction ORIG000001 has been reversed back into your account")
        assertEquals(MpesaKind.REVERSAL, result.kind)
        assertEquals("ORIG000001", result.originalReference)
        assertEquals("expense", result.direction)
        assertEquals("0.00", result.feeRefundAmount)
        assertFalse(parser.parse("MPESA", text("Reversal requested for ORIG000001 Ksh214.25")) is MpesaParseResult.Parsed)
    }

    @Test fun deterministicCenturyMidnightNoonAndNbsp() {
        val body = text("You bought Ksh\u00a075.00 of airtime")
        assertEquals("2026-10-10T21:00:00Z", (parser.parse("MPESA", body.replace("7:39 PM", "12:00 AM")) as MpesaParseResult.Parsed).event.timestamp)
        assertEquals("2026-10-11T09:00:00Z", (parser.parse("MPESA", body.replace("7:39 PM", "12:00 PM")) as MpesaParseResult.Parsed).event.timestamp)
    }

    @Test fun malformedFeesNeverSilentlyBecomeZero() {
        for (fee in listOf("0.001", "-7.00", "NaN", "1,23.00")) {
            assertFalse(parser.parse("MPESA", text("Ksh120.00 sent to Example") + " Transaction cost, Ksh$fee.") is MpesaParseResult.Parsed)
        }
        assertFalse(parser.parse("MPESA", text("Ksh120.00 sent to Example") + " Transaction cost, Ksh7.00. Transaction cost, Ksh7.00.") is MpesaParseResult.Parsed)
    }

    @Test fun financialDateMustBelongToTheMatchedFamily() {
        assertFalse(parser.parse("MPESA", text("Ksh120.00 sent to Example on invalid time. Promotional offer")) is MpesaParseResult.Parsed)
        assertFalse(parser.parse("MPESA", text("Ksh120.00 sent to Example").replace("11/10/26", "11/10/1999")) is MpesaParseResult.Parsed)
        assertEquals("2099-10-11T16:39:00Z", (parser.parse("MPESA", text("Ksh120.00 sent to Example").replace("11/10/26", "11/10/99")) as MpesaParseResult.Parsed).event.timestamp)
    }

    @Test fun phoneOnlyCounterpartyAndBillAccountsAreNotExported() {
        assertNull(parsed("Ksh120.00 sent to 0700000001").merchant)
        assertNull(parsed("You have received Ksh120.00 from 0700***002").merchant)
        val keys = parsed("Ksh120.00 paid to Example").normalized().keys
        assertEquals(setOf("external_reference", "transaction_timestamp", "kind", "parser_version", "amount", "transaction_type", "transaction_cost", "category", "merchant"), keys)
    }

    @Test fun reversalFeeAndSelfReferenceAreStrict() {
        val body = text("Ksh214.25 from transaction ORIG000001 has been reversed back into your account")
        val refunded = parser.parse("MPESA", body + " Transaction fee refunded, Ksh8.50.") as MpesaParseResult.Parsed
        assertEquals("8.50", refunded.event.feeRefundAmount)
        assertFalse(parser.parse("MPESA", body.replace("ORIG000001", "TEST000001")) is MpesaParseResult.Parsed)
        assertFalse(parser.parse("MPESA", body + " Transaction fee refunded, Ksh0.001.") is MpesaParseResult.Parsed)
    }
}
