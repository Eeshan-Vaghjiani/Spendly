package com.evagh.capstone.spending_support.mpesa

import org.junit.Assert.*
import org.junit.Test

class SmsCleanupTest {
    @Test fun failuresDoNotSkipRemainingStopsOrCredentialErasure() {
        val calls = mutableListOf<String>()
        val first = IllegalStateException("fixture cancellation failure")
        try {
            runSmsCleanup(
                { calls.add("receiver") },
                { calls.add("request"); throw first },
                { calls.add("jobs"); throw IllegalStateException("fixture job failure") },
                { calls.add("erase") },
            )
            fail("Incomplete cleanup must still be reported to the auth boundary")
        } catch (error: IllegalStateException) {
            assertSame(first, error)
            assertEquals(1, error.suppressed.size)
        }
        assertEquals(listOf("receiver", "request", "jobs", "erase"), calls)
    }
}
