package com.evagh.capstone.spending_support.mpesa

import java.io.ByteArrayOutputStream
import java.io.InputStream

internal fun InputStream.readBounded(limit: Int): ByteArray {
    val output = ByteArrayOutputStream()
    val buffer = ByteArray(4096)
    while (output.size() <= limit) {
        val read = read(buffer, 0, minOf(buffer.size, limit + 1 - output.size()))
        if (read < 0) return output.toByteArray()
        output.write(buffer, 0, read)
    }
    throw IllegalArgumentException("Input exceeded its bounded size")
}
