package com.evagh.capstone.spending_support.mpesa

import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

class CancelableSmsRequestTest {
    @Test fun failingDisconnectStillFencesIoAndLeavesCancellationPermanent() {
        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val disconnected = CountDownLatch(1)
        val request = CancelableSmsRequest { disconnected.countDown(); throw IllegalStateException("fixture close failure") }
        val pool = Executors.newFixedThreadPool(2)
        try {
            val worker = pool.submit { request.io { entered.countDown(); check(release.await(2, TimeUnit.SECONDS)) } }
            assertTrue(entered.await(2, TimeUnit.SECONDS))
            val stopped = pool.submit { request.cancel() }
            assertTrue(disconnected.await(2, TimeUnit.SECONDS))
            assertFalse(stopped.isDone)
            release.countDown()
            worker.get(2, TimeUnit.SECONDS)
            try { stopped.get(2, TimeUnit.SECONDS); fail("Expected fixture close failure") }
            catch (_: java.util.concurrent.ExecutionException) { }
            try { request.io { fail("Cancelled after failed disconnect") }; fail("Cancellation must persist") }
            catch (_: IllegalStateException) { }
        } finally { release.countDown(); pool.shutdownNow() }
    }

    @Test fun disabledAfterRegistrationNeverStartsFirstIo() {
        val starts = AtomicInteger()
        val closed = AtomicInteger()
        val request = CancelableSmsRequest { closed.incrementAndGet() }
        // Worker is registered but paused. Disable/account switch completes.
        request.cancel()
        try {
            request.io { starts.incrementAndGet() }
            fail("Cancelled request must not start a socket operation")
        } catch (_: IllegalStateException) { }
        assertEquals(0, starts.get())
        assertEquals(1, closed.get())
    }

    @Test fun cancellationInterruptsAndFencesActiveIoAndRejectsLaterBodyWrite() {
        val entered = CountDownLatch(1)
        val interrupted = CountDownLatch(1)
        val request = CancelableSmsRequest { interrupted.countDown() }
        val pool = Executors.newFixedThreadPool(2)
        try {
            val worker = pool.submit<Int> { request.io {
                entered.countDown()
                check(interrupted.await(2, TimeUnit.SECONDS))
                1
            } }
            assertTrue(entered.await(2, TimeUnit.SECONDS))
            val stopped = pool.submit { request.cancel() }
            stopped.get(2, TimeUnit.SECONDS)
            assertEquals(1, worker.get(2, TimeUnit.SECONDS).toInt())
            try { request.io { fail("No subsequent body or response I/O") }; fail("Cancellation must persist") }
            catch (_: IllegalStateException) { }
        } finally { pool.shutdownNow() }
    }
}
