package com.evagh.capstone.spending_support.mpesa

import android.app.job.JobParameters
import android.app.job.JobService

class MpesaJobService : JobService() {
    override fun onStartJob(params: JobParameters): Boolean {
        MpesaImporter.executor.execute {
            val result = MpesaImporter.sync(applicationContext)
            jobFinished(params, result["active"] == true && (result["error"] != null || result["history_pending"] == true || (result["pending"] as? Int ?: 0) > 0))
        }
        return true
    }
    override fun onStopJob(params: JobParameters): Boolean {
        MpesaImporter.controlExecutor.execute { MpesaImporter.cancelWork(applicationContext) }
        return true
    }
}
