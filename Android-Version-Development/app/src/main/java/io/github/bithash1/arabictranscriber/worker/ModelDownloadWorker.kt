package io.github.bithash1.arabictranscriber.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.WorkerParameters
import io.github.bithash1.arabictranscriber.TranscriberApplication
import io.github.bithash1.arabictranscriber.model.ModelAvailability
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import kotlin.coroutines.coroutineContext

class ModelDownloadWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val modelId = inputData.getString(KEY_MODEL_ID) ?: return@withContext Result.failure()
        val app = applicationContext as TranscriberApplication
        val manager = app.modelManager
        val spec = runCatching { manager.spec(modelId) }.getOrElse {
            return@withContext Result.failure(errorData(it.message ?: "模型配置无效"))
        }
        if (manager.availability(modelId) == ModelAvailability.DOWNLOADED) {
            return@withContext Result.success(Data.Builder().putString(KEY_MODEL_ID, modelId).build())
        }
        setForeground(
            WorkerNotifications.create(
                applicationContext,
                modelId.hashCode(),
                "正在下载 ${spec.label} 模型",
                "准备下载",
                0,
            ),
        )

        val target = manager.modelFile(modelId)
        val partial = manager.partialFile(modelId)
        if (target.exists()) target.delete()

        try {
            var downloaded = if (partial.exists()) partial.length() else 0L
            val connection = (URL(spec.url).openConnection() as HttpURLConnection).apply {
                connectTimeout = 30_000
                readTimeout = 60_000
                instanceFollowRedirects = true
                if (downloaded > 0) setRequestProperty("Range", "bytes=$downloaded-")
            }
            connection.connect()
            if (downloaded > 0 && connection.responseCode != HttpURLConnection.HTTP_PARTIAL) {
                partial.delete()
                downloaded = 0L
            }
            if (connection.responseCode !in 200..299) {
                return@withContext Result.retry()
            }
            val remaining = connection.contentLengthLong.coerceAtLeast(0L)
            val total = when {
                connection.responseCode == HttpURLConnection.HTTP_PARTIAL -> downloaded + remaining
                remaining > 0 -> remaining
                else -> -1L
            }
            var lastReportedProgress = -1
            BufferedInputStream(connection.inputStream).use { input ->
                BufferedOutputStream(FileOutputStream(partial, downloaded > 0)).use { output ->
                    val buffer = ByteArray(DEFAULT_BUFFER_SIZE * 8)
                    while (true) {
                        coroutineContext.ensureActive()
                        val count = input.read(buffer)
                        if (count < 0) break
                        output.write(buffer, 0, count)
                        downloaded += count
                        if (total > 0) {
                            val progress = ((downloaded * 100) / total).toInt().coerceIn(0, 100)
                            setProgress(
                                Data.Builder()
                                    .putString(KEY_MODEL_ID, modelId)
                                    .putInt(KEY_PROGRESS, progress)
                                    .build(),
                            )
                            if (progress != lastReportedProgress) {
                                setForeground(
                                    WorkerNotifications.create(
                                        applicationContext,
                                        modelId.hashCode(),
                                        "正在下载 ${spec.label} 模型",
                                        "$progress%",
                                        progress,
                                    ),
                                )
                                lastReportedProgress = progress
                            }
                        }
                    }
                }
            }
            connection.disconnect()
            if (!manager.isValidModelFile(partial, spec)) {
                partial.delete()
                return@withContext Result.failure(errorData("模型文件不完整，请重新下载。"))
            }
            if (!partial.renameTo(target)) {
                return@withContext Result.failure(errorData("无法保存下载完成的模型。"))
            }
            Result.success(Data.Builder().putString(KEY_MODEL_ID, modelId).build())
        } catch (error: Exception) {
            if (runAttemptCount < 2) Result.retry()
            else Result.failure(errorData(error.message ?: "模型下载失败"))
        }
    }

    private fun errorData(message: String) = Data.Builder().putString(KEY_ERROR, message).build()

    companion object {
        const val KEY_MODEL_ID = "model_id"
        const val KEY_PROGRESS = "progress"
        const val KEY_ERROR = "error"
    }
}
