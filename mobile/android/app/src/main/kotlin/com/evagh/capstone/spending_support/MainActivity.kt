package com.evagh.capstone.spending_support

import android.Manifest
import com.evagh.capstone.spending_support.mpesa.MpesaImporter
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import io.flutter.plugin.common.EventChannel
import android.os.Handler
import android.os.Looper
import org.json.JSONArray

class MainActivity : FlutterActivity() {
    private var permissionResult: MethodChannel.Result? = null

    override fun configureFlutterEngine(engine: FlutterEngine) {
        super.configureFlutterEngine(engine)
        if (!MpesaImporter.capability()) MpesaImporter.controlExecutor.execute { try { MpesaImporter.disable(applicationContext) } catch (_: Exception) {} }
        EventChannel(engine.dartExecutor.binaryMessenger, "spendly/mpesa_changes").setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, events: EventChannel.EventSink) {
                MpesaImporter.financialChanged = { Handler(Looper.getMainLooper()).post { events.success(true) }; Unit }
            }
            override fun onCancel(arguments: Any?) { MpesaImporter.financialChanged = null }
        })
        MethodChannel(engine.dartExecutor.binaryMessenger, "spendly/mpesa_sms").setMethodCallHandler { call, result ->
            if (call.method == "permission") { result.success(MpesaImporter.permission(this)); return@setMethodCallHandler }
            if (call.method == "requestPermission") {
                if (!MpesaImporter.hasConsent(this) || call.argument<Boolean>("accepted") != true ||
                    call.argument<String>("consent_version") != MpesaImporter.CONSENT_VERSION) {
                    result.error("DISCLOSURE_REQUIRED", "Accept the SMS disclosure first.", null)
                } else if (permissionResult != null) {
                    result.error("BUSY", "Permission request is already open.", null)
                } else if (MpesaImporter.permission(this)) result.success(true)
                else {
                    permissionResult = result
                    requestPermissions(arrayOf(Manifest.permission.READ_SMS, Manifest.permission.RECEIVE_SMS), 38003)
                }
                return@setMethodCallHandler
            }
            val task: () -> Unit = {
                try {
                    val value: Any? = when (call.method) {
                        "status" -> MpesaImporter.status(applicationContext)
                        "disable" -> { MpesaImporter.disable(applicationContext); null }
                        "enable" -> {
                            MpesaImporter.enable(applicationContext, call.argument<String>("account_id")!!,
                                call.argument<String>("token")!!, call.argument<String>("base_url")!!,
                                call.argument<String>("consent_version")!!)
                            null
                        }
                        "refreshSession" -> {
                            MpesaImporter.refreshSession(applicationContext, call.argument<String>("account_id")!!, call.argument<String>("token")!!)
                            null
                        }
                        "historical" -> {
                            MpesaImporter.historical(applicationContext, call.argument<Int>("days")!!)
                            null
                        }
                        "sync" -> MpesaImporter.sync(applicationContext)
                        "fixtures" -> {
                            MpesaImporter.fixtures(applicationContext, JSONArray(call.argument<List<Map<String, Any>>>("messages")), call.argument<Boolean>("permission") == true)
                            MpesaImporter.status(applicationContext)
                        }
                        "deliverFixture" -> {
                            MpesaImporter.deliverFixture(applicationContext, call.argument<String>("sender")!!, call.argument<String>("body")!!)
                            MpesaImporter.status(applicationContext)
                        }
                        else -> throw IllegalArgumentException()
                    }
                    runOnUiThread { result.success(value) }
                } catch (error: Exception) {
                    val details = if (BuildConfig.DEBUG) mapOf("reason" to error.javaClass.simpleName) else null
                    runOnUiThread { result.error("SMS_IMPORT_ERROR", "SMS import could not complete safely. Retry or turn it off.", details) }
                }
            }
            if (call.method == "sync") MpesaImporter.executor.execute(task) else MpesaImporter.controlExecutor.execute(task)
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 38003) {
            permissionResult?.success(MpesaImporter.permission(this))
            permissionResult = null
            MpesaImporter.permissionResolved(applicationContext)
        }
    }

    override fun onDestroy() {
        MpesaImporter.financialChanged = null
        permissionResult?.error("CANCELLED", "Permission request was interrupted. Review the disclosure again.", null)
        permissionResult = null
        super.onDestroy()
    }
}
