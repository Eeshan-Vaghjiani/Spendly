package com.evagh.capstone.spending_support.mpesa

import android.Manifest
import android.app.job.JobInfo
import android.app.job.JobScheduler
import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import android.database.Cursor
import android.os.CancellationSignal
import android.os.Build
import android.provider.Telephony
import android.util.Base64
import com.evagh.capstone.spending_support.BuildConfig
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors
import java.util.concurrent.locks.ReentrantLock

/** One process coordinator. Generations fence every read, parse, queue and upload. */
object MpesaImporter {
    const val CONSENT_VERSION = "2026-10-22"
    private const val JOB_PERIODIC = 38001
    private const val JOB_NOW = 38002
    private const val MAX_QUEUE = 1500
    private val lock = Any()
    private val syncLock = ReentrantLock()
    val executor = Executors.newSingleThreadExecutor()
    val controlExecutor = Executors.newSingleThreadExecutor()
    val receiverExecutor = Executors.newSingleThreadExecutor()
    private var state: JSONObject? = null
    private var blocked = false
    private var signal: CancellationSignal? = null
    private var connection: CancelableSmsRequest? = null
    private var fixtureMessages = JSONArray()
    private var fixturePermission: Boolean? = null
    private var readCount = 0
    private val parser = MpesaSmsParser()
    @Volatile var financialChanged: (() -> Unit)? = null

    private fun tokenMatches(token: String, account: String): Boolean = try {
        val parts = token.split('.')
        token.length <= 8192 && parts.size == 3 && JSONObject(String(Base64.decode(parts[1], Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING), Charsets.UTF_8)).optString("sub") == account
    } catch (_: Exception) { false }

    private fun isAcceptance(context: Context) = context.packageName.endsWith(".acceptance")
    private fun emulatorLab(context: Context) = isAcceptance(context) && BuildConfig.MPESA_SMS_EMULATOR_LAB &&
        Build.HARDWARE in setOf("ranchu", "goldfish") && (Build.FINGERPRINT.contains("generic") || Build.PRODUCT.contains("sdk"))
    private fun safeTarget(context: Context) = !isAcceptance(context) || BuildConfig.MPESA_SMS_TEST_SOURCE || emulatorLab(context)
    private fun receiverEnabled(context: Context) = context.packageManager.getComponentEnabledSetting(
        ComponentName(context, MpesaSmsReceiver::class.java)) == PackageManager.COMPONENT_ENABLED_STATE_ENABLED
    private fun setReceiver(context: Context, enabled: Boolean) {
        if (!capability()) return
        context.packageManager.setComponentEnabledSetting(ComponentName(context, MpesaSmsReceiver::class.java),
            if (enabled) PackageManager.COMPONENT_ENABLED_STATE_ENABLED else PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
            PackageManager.DONT_KILL_APP)
    }
    fun capability() = BuildConfig.MPESA_SMS_CAPABILITY
    fun hasConsent(context: Context): Boolean = synchronized(lock) {
        capability() && safeTarget(context) && !blocked && data(context).optBoolean("enabled") && data(context).optString("consent_version") == CONSENT_VERSION
    }
    private fun data(context: Context): JSONObject {
        if (state == null) {
            state = try { MpesaStateStore(context).read() }
            catch (_: Exception) { blocked = true; JSONObject().put("enabled", false).put("generation", 0L)
                .put("error", "Local import state is unavailable. Turn import off, then enable it again.") }
        }
        return state!!
    }
    private fun persist(context: Context) {
        try { MpesaStateStore(context).write(data(context)) }
        catch (error: Exception) {
            blocked = true
            data(context).put("error", "Local import state could not be saved. Turn import off before retrying.")
            throw error
        }
    }
    fun permission(context: Context): Boolean {
        if (isAcceptance(context) && BuildConfig.MPESA_SMS_TEST_SOURCE) fixturePermission?.let { return it }
        return listOf(Manifest.permission.READ_SMS, Manifest.permission.RECEIVE_SMS).all {
            context.checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED
        }
    }
    private fun active(context: Context, generation: Long? = null): Boolean {
        if (!capability() || !safeTarget(context) || blocked || !permission(context) || !receiverEnabled(context)) return false
        val current = data(context)
        return current.optBoolean("enabled") && current.optString("consent_version") == CONSENT_VERSION &&
            current.optString("account_id").isNotBlank() && current.optString("token").isNotBlank() &&
            (generation == null || generation == current.optLong("generation"))
    }
    fun status(context: Context): Map<String, Any?> = synchronized(lock) {
        val current = data(context)
        mapOf("available" to capability(), "enabled" to (current.optBoolean("enabled") && !blocked),
            "permission" to permission(context), "active" to active(context),
            "pending" to current.optJSONArray("queue")?.length().orZero(),
            "history_pending" to current.optBoolean("history_pending"),
            "test_sms_reads" to if (isAcceptance(context)) readCount else null,
            "emulator_lab" to emulatorLab(context),
            "last_sync" to current.optLong("last_sync").takeIf { it > 0 },
            "summary" to (current.optJSONObject("summary")?.let { jsonMap(it) } ?: emptyMap<String, Any?>()),
            "error" to current.optString("error").takeIf { it.isNotBlank() })
    }
    private fun Int?.orZero() = this ?: 0
    private fun jsonMap(value: JSONObject): Map<String, Any?> = value.keys().asSequence().associateWith { key ->
        value.opt(key).takeUnless { it == JSONObject.NULL }
    }
    fun enable(context: Context, account: String, token: String, base: String, consent: String) = synchronized(lock) {
        require(capability() && safeTarget(context) && consent == CONSENT_VERSION && account.isNotBlank() && tokenMatches(token, account))
        val url = URL(base)
        require((url.protocol == "https" && url.userInfo == null) ||
            (isAcceptance(context) && url.protocol == "http" && url.host in setOf("127.0.0.1", "10.0.2.2") && url.port == 5057))
        require(url.path.trimEnd('/') == "/api/v1" && url.query == null && url.ref == null)
        val previous = data(context)
        val generation = previous.optLong("generation") + 1
        val resume = previous.optBoolean("enabled") && previous.optString("account_id") == account && previous.optString("consent_version") == consent
        blocked = true
        signal?.cancel(); connection?.cancel()
        state = (if (resume) previous else JSONObject().put("queue", JSONArray()).put("cursor_date", System.currentTimeMillis()).put("cursor_id", -1L))
            .put("account_id", account).put("token", token).put("base", base.trimEnd('/'))
            .put("enabled", true).put("consent_version", consent).put("generation", generation)
        try { persist(context); blocked = false } catch (error: Exception) { throw error }
        setReceiver(context, permission(context))
        schedule(context)
    }
    /** Fail closed in memory even if disk write fails. Caller must not finish logout on failure. */
    fun disable(context: Context) = synchronized(lock) {
        blocked = true
        val generation = data(context).optLong("generation") + 1
        state = JSONObject().put("enabled", false).put("generation", generation)
        val scheduler = context.getSystemService(JobScheduler::class.java)
        try { runSmsCleanup(
            { setReceiver(context, false) },
            { signal?.cancel() },
            { connection?.cancel() },
            { scheduler.cancel(JOB_NOW) },
            { scheduler.cancel(JOB_PERIODIC) },
            { MpesaStateStore(context).erase() },
        ) } catch (error: Exception) {
            data(context).put("error", "Import is stopped. Clear local import data before enabling it again.")
            throw error
        }
        blocked = false
    }
    fun refreshSession(context: Context, account: String, token: String) = synchronized(lock) {
        require(tokenMatches(token, account))
        val current = data(context)
        if (current.optBoolean("enabled") && current.optString("account_id") != account) disable(context)
        else if (current.optBoolean("enabled")) { current.put("token", token); persist(context); schedule(context) }
    }
    fun permissionResolved(context: Context) = synchronized(lock) {
        setReceiver(context, hasConsent(context) && permission(context))
        schedule(context)
    }
    fun historical(context: Context, days: Int) = synchronized(lock) {
        require(days in setOf(0, 30, 90) && active(context))
        cancelWork(context)
        data(context).put("cursor_date", if (days == 0) 0L else System.currentTimeMillis() - days * 86_400_000L)
            .put("cursor_id", -1L)
        persist(context); schedule(context)
    }
    fun schedule(context: Context) = synchronized(lock) {
        if (!active(context)) return@synchronized
        val component = ComponentName(context, MpesaJobService::class.java)
        val scheduler = context.getSystemService(JobScheduler::class.java)
        if (!syncLock.isLocked) scheduler.schedule(JobInfo.Builder(JOB_NOW, component).setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setMinimumLatency(1000).setBackoffCriteria(30_000, JobInfo.BACKOFF_POLICY_EXPONENTIAL).build())
        if (scheduler.getPendingJob(JOB_PERIODIC) == null) scheduler.schedule(JobInfo.Builder(JOB_PERIODIC, component).setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
            .setPeriodic(15 * 60_000L).setPersisted(true).build())
    }
    /** Called only after receiver consent gate, before it decodes any SMS PDUs. */
    fun mayReceive(context: Context): Boolean = synchronized(lock) { (!isAcceptance(context) || emulatorLab(context)) && active(context) }
    fun withReceiveGate(context: Context, action: () -> Unit) = synchronized(lock) {
        if ((!isAcceptance(context) || emulatorLab(context)) && active(context)) action()
    }
    fun receive(context: Context, sender: String?, body: String) = synchronized(lock) {
        if (!active(context) || !MpesaSmsParser.allowedSender(sender)) return@synchronized
        val current = data(context)
        val summary = current.optJSONObject("summary") ?: JSONObject()
        accept(context, sender, body, summary)
        current.put("summary", summary); persist(context); schedule(context)
    }
    private fun increment(summary: JSONObject, key: String, count: Int = 1) {
        summary.put(key, summary.optInt(key) + count)
    }
    private fun accept(context: Context, sender: String?, body: String, summary: JSONObject): Boolean {
        if (!active(context) || !MpesaSmsParser.allowedSender(sender)) return false
        val queue = data(context).optJSONArray("queue") ?: JSONArray()
        if (queue.length() >= MAX_QUEUE) { data(context).put("error", "Pending import is full. Connect and sync before reading more."); return false }
        increment(summary, "checked")
        when (val parsed = parser.parse(sender, body)) {
            is MpesaParseResult.Parsed -> {
                increment(summary, "valid")
                val value = JSONObject(parsed.event.normalized())
                for (index in 0 until queue.length()) {
                    if (queue.getJSONObject(index).optString("external_reference") == parsed.event.transactionCode) {
                        increment(summary, if (queue.getJSONObject(index).toString() == value.toString()) "duplicate" else "invalid")
                        return true
                    }
                }
                queue.put(value); data(context).put("queue", queue)
            }
            MpesaParseResult.Unsupported -> increment(summary, "unsupported")
            MpesaParseResult.Invalid -> increment(summary, "invalid")
        }
        return true
    }
    private fun scan(context: Context, generation: Long, summary: JSONObject): Int {
        if (isAcceptance(context) && BuildConfig.MPESA_SMS_TEST_SOURCE) {
            require(BuildConfig.MPESA_SMS_TEST_SOURCE)
            synchronized(lock) {
                if (!active(context, generation)) return 0
                val current = data(context)
                val selected = (0 until fixtureMessages.length()).map { fixtureMessages.getJSONObject(it) }
                    .filter { MpesaSmsParser.allowedSender(it.optString("sender")) &&
                        (it.getLong("date") > current.optLong("cursor_date") ||
                        (it.getLong("date") == current.optLong("cursor_date") && it.getLong("id") > current.optLong("cursor_id"))) }
                    .sortedWith(compareBy({ it.getLong("date") }, { it.getLong("id") })).take(200)
                for (row in selected) {
                    if (!active(context, generation)) return 0
                    readCount++
                    if (!accept(context, row.optString("sender"), row.optString("body"), summary)) { persist(context); return 200 }
                    current.put("cursor_date", row.getLong("date")).put("cursor_id", row.getLong("id"))
                }
                persist(context)
                return selected.size
            }
        }
        val query = synchronized(lock) {
            if (!active(context, generation)) return 0
            val current = data(context)
            val cancel = CancellationSignal().also { signal = it }
            Triple(current.optLong("cursor_date"), current.optLong("cursor_id"), cancel)
        }
        // Provider filters and projection never enumerate unrelated conversations.
        val cursor: Cursor? = synchronized(lock) {
            if (!active(context, generation)) return 0
            context.contentResolver.query(Telephony.Sms.Inbox.CONTENT_URI,
                arrayOf("_id", "date", "address", "body"),
                "(TRIM(address) = ? COLLATE NOCASE OR TRIM(address) = ? COLLATE NOCASE) AND (date > ? OR (date = ? AND _id > ?))",
                arrayOf("MPESA", "M-PESA", query.first.toString(), query.first.toString(), query.second.toString()),
                "date ASC, _id ASC LIMIT 200", query.third)
        }
        var count = 0
        cursor?.use { rows ->
            while (true) {
                synchronized(lock) {
                    if (!active(context, generation)) return count
                    if (!rows.moveToNext()) { persist(context); return count }
                    val sender = rows.getString(2)
                    if (!MpesaSmsParser.allowedSender(sender)) return@synchronized
                    readCount++
                    if (!accept(context, sender, rows.getString(3).orEmpty(), summary)) { persist(context); return 200 }
                    count++
                    data(context).put("cursor_date", rows.getLong(1)).put("cursor_id", rows.getLong(0))
                }
            }
        }
        return count
    }
    private fun request(context: Context, generation: Long, path: String, payload: JSONObject? = null): JSONObject {
        val snapshot = synchronized(lock) {
            check(active(context, generation))
            data(context).optString("base") to data(context).optString("token")
        }
        val transport = URL(snapshot.first + path).openConnection() as HttpURLConnection
        val guarded = CancelableSmsRequest { transport.disconnect() }
        try {
            transport.connectTimeout = 8_000; transport.readTimeout = 12_000
            transport.instanceFollowRedirects = false
            transport.setRequestProperty("Authorization", "Bearer " + snapshot.second)
            transport.setRequestProperty("Content-Type", "application/json")
            if (payload != null) { transport.requestMethod = "POST"; transport.doOutput = true }
            synchronized(lock) { check(active(context, generation)); connection = guarded }
            if (payload != null) {
                guarded.io { transport.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) } }
            }
            val status = guarded.io { transport.responseCode }
            synchronized(lock) {
                check(active(context, generation))
                if (status in setOf(401, 403)) {
                    disable(context)
                    throw IllegalStateException("SMS import paused. Sign in and enable it again.")
                }
            }
            check(status == 200)
            val text = guarded.io { transport.inputStream.use { String(it.readBounded(100_000), Charsets.UTF_8) } }
            require(text.length <= 100_000)
            val response = JSONObject(text)
            require(response.optBoolean("success"))
            return response.getJSONObject("data")
        } finally { guarded.cancel(); synchronized(lock) { if (connection === guarded) connection = null } }
    }
    fun sync(context: Context): Map<String, Any?> {
        if (!syncLock.tryLock()) return status(context)
        var generation = -1L
        try {
            generation = synchronized(lock) { if (!active(context)) return status(context); data(context).optLong("generation") }
            val server = request(context, generation, "/mpesa/settings")
            val account = synchronized(lock) { data(context).optString("account_id") }
            if (server.optString("account_id") != account || !server.optBoolean("enabled") || !server.optBoolean("available") || server.optString("consent_version") != CONSENT_VERSION) {
                synchronized(lock) { if (active(context, generation)) disable(context) }; return status(context)
            }
            val summary = JSONObject()
            var moreHistory = false
            for (page in 0 until 5) {
                moreHistory = scan(context, generation, summary) == 200
                if (!moreHistory) break
            }
            synchronized(lock) {
                if (active(context, generation)) { data(context).put("history_pending", moreHistory); persist(context) }
            }
            while (true) {
                val batch = synchronized(lock) {
                    if (!active(context, generation)) return status(context)
                    val pending = data(context).optJSONArray("queue") ?: JSONArray()
                    JSONArray().also { selected -> for (index in 0 until minOf(50, pending.length())) selected.put(pending.getJSONObject(index)) }
                }
                if (batch.length() == 0) break
                val result = request(context, generation, "/transactions/mpesa/import", JSONObject().put("events", batch))
                val results = result.getJSONArray("results")
                require(results.length() == batch.length())
                val seen = mutableSetOf<Int>()
                for (index in 0 until results.length()) {
                    val row = results.getJSONObject(index)
                    require(row.getInt("index") in 0 until batch.length() && seen.add(row.getInt("index")))
                    require(row.getString("status") in setOf("created", "duplicate", "invalid", "needs_review", "reversed", "pending_reversal", "reconciled"))
                }
                synchronized(lock) {
                    if (!active(context, generation)) return status(context)
                    val pending = data(context).getJSONArray("queue")
                    val retained = JSONArray()
                    val references = (0 until batch.length()).map { batch.getJSONObject(it).getString("external_reference") }.toSet()
                    for (index in 0 until pending.length()) if (pending.getJSONObject(index).optString("external_reference") !in references) retained.put(pending.getJSONObject(index))
                    data(context).put("queue", retained)
                    for (key in listOf("created", "duplicate", "invalid", "needs_review", "reversals")) increment(summary, key, result.optInt(key))
                    data(context).put("summary", summary); persist(context)
                    if (result.optInt("created") > 0 || result.optInt("reversals") > 0) financialChanged?.invoke()
                }
            }
            synchronized(lock) {
                if (active(context, generation)) {
                    data(context).put("summary", summary).put("last_sync", System.currentTimeMillis()).remove("error")
                    persist(context)
                }
            }
        } catch (error: Exception) {
            if (BuildConfig.DEBUG) android.util.Log.d("SpendlySms", "Sync paused (" + error.javaClass.simpleName + ")")
            synchronized(lock) {
                if (generation >= 0 && active(context, generation)) {
                    data(context).put("error", "Sync paused. Check your connection and retry; pending records are kept safely.")
                    try { persist(context) } catch (_: Exception) { blocked = true }
                }
            }
        } finally { syncLock.unlock() }
        return status(context)
    }
    fun fixtures(context: Context, messages: JSONArray, allowed: Boolean) = synchronized(lock) {
        require(isAcceptance(context) && BuildConfig.MPESA_SMS_TEST_SOURCE)
        require(messages.length() <= 100)
        fixtureMessages = messages; fixturePermission = allowed
    }
    fun cancelWork(context: Context) = synchronized(lock) {
        signal?.cancel(); connection?.cancel()
        data(context).put("generation", data(context).optLong("generation") + 1)
        try { persist(context) } catch (_: Exception) { blocked = true }
    }
    fun deliverFixture(context: Context, sender: String, body: String) {
        require(isAcceptance(context) && BuildConfig.MPESA_SMS_TEST_SOURCE)
        receive(context, sender, body)
    }
}
