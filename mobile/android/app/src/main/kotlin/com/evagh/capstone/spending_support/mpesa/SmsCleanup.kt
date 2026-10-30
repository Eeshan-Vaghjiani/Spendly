package com.evagh.capstone.spending_support.mpesa

/** A cancellation/component failure must never skip credential erasure. */
internal fun runSmsCleanup(vararg operations: () -> Unit) {
    var failure: Exception? = null
    for (operation in operations) {
        try { operation() }
        catch (error: Exception) {
            if (failure == null) failure = error else failure.addSuppressed(error)
        }
    }
    failure?.let { throw it }
}
