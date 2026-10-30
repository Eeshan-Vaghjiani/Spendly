package com.evagh.capstone.spending_support.mpesa

/** Cancellation is permanent, including before the first socket operation. */
class CancelableSmsRequest(private val disconnect: () -> Unit) {
    private val gate = Any()
    @Volatile private var cancelled = false

    fun <T> io(operation: () -> T): T = synchronized(gate) {
        check(!cancelled) { "Import request cancelled" }
        operation()
    }

    fun cancel() {
        cancelled = true
        // Interrupt an ongoing socket operation before waiting for its fence.
        // io() never acquires the importer's state lock, avoiding lock inversion.
        try { disconnect() }
        finally { synchronized(gate) { /* Any already-started I/O has now finished. */ } }
    }
}
