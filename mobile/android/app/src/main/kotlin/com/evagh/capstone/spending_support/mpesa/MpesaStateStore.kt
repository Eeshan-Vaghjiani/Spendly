package com.evagh.capstone.spending_support.mpesa

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import org.json.JSONObject
import java.io.File
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** No SMS body is accepted by this store. Backups are disabled by the manifest. */
class MpesaStateStore(context: Context) {
    private val file = AtomicFile(File(context.noBackupFilesDir, "mpesa-normalized-v1"))
    private val alias = "spendly-mpesa-state-v1"
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    fun read(): JSONObject {
        if (!file.baseFile.exists()) return JSONObject().put("enabled", false).put("generation", 0L)
        val bytes = file.openRead().use { input ->
            val data = input.readBounded(2_000_000)
            require(data.size <= 2_000_000); data
        }
        require(bytes.size >= 29 && bytes[0] == 1.toByte())
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(1, 13)))
        val state = JSONObject(String(cipher.doFinal(bytes.copyOfRange(13, bytes.size)), Charsets.UTF_8))
        require(state.optInt("format") == 1 && state.has("generation"))
        return state
    }
    fun write(state: JSONObject) {
        state.put("format", 1)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encrypted = byteArrayOf(1) + cipher.iv + cipher.doFinal(state.toString().toByteArray(Charsets.UTF_8))
        require(encrypted.size <= 2_000_000)
        val output = file.startWrite()
        try { output.write(encrypted); file.finishWrite(output) }
        catch (error: Exception) { file.failWrite(output); throw error }
    }
    fun erase() {
        // Crypto-erasure prevents a failed file deletion or old AtomicFile
        // backup from restoring credentials/queued events after sign-out.
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        try { if (store.containsAlias(alias)) store.deleteEntry(alias) }
        finally { file.delete() }
    }
}
