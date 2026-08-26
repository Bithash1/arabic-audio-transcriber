package io.github.bithash1.arabictranscriber.worker

import android.content.Context
import android.net.Uri
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.WorkerParameters
import io.github.bithash1.arabictranscriber.TranscriberApplication
import io.github.bithash1.arabictranscriber.model.TaskStatus
import io.github.bithash1.arabictranscriber.model.TranscriptionRecord
import io.github.bithash1.arabictranscriber.transcription.AudioDecoder
import io.github.bithash1.arabictranscriber.transcription.WhisperEngine
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

class TranscriptionWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val recordId = inputData.getString(KEY_RECORD_ID) ?: return@withContext Result.failure()
        val sourceUri = inputData.getString(KEY_SOURCE_URI)?.let(Uri::parse) ?: return@withContext Result.failure()
        val sourceName = inputData.getString(KEY_SOURCE_NAME) ?: "未命名音频"
        val modelId = inputData.getString(KEY_MODEL_ID) ?: "medium"
        val app = applicationContext as TranscriberApplication
        val history = app.historyStore
        val existing = history.get(recordId) ?: TranscriptionRecord(
            id = recordId,
            sourceName = sourceName,
            modelId = modelId,
            createdAt = System.currentTimeMillis(),
            updatedAt = System.currentTimeMillis(),
            status = TaskStatus.QUEUED,
        )
        val taskDirectory = File(applicationContext.cacheDir, "transcription/$recordId")
        val temporaryMedia = File(taskDirectory, "source-media")
        taskDirectory.mkdirs()

        try {
            setForeground(
                WorkerNotifications.create(
                    applicationContext,
                    recordId.hashCode(),
                    "正在转写 ${existing.sourceName}",
                    "准备任务",
                    0,
                ),
            )
            history.upsert(existing.copy(status = TaskStatus.RUNNING, updatedAt = System.currentTimeMillis()))
            setStage(STAGE_COPYING, 5)
            applicationContext.contentResolver.openInputStream(sourceUri).use { input ->
                requireNotNull(input) { "无法读取所选媒体文件。" }
                temporaryMedia.outputStream().buffered().use { output -> input.copyTo(output) }
            }

            setStage(STAGE_DECODING, 15)
            val samples = AudioDecoder().decodeTo16KhzMono(temporaryMedia)
            require(samples.isNotEmpty()) { "媒体文件中没有可转写的音频。" }

            setStage(STAGE_TRANSCRIBING, 30)
            val modelFile = app.modelManager.modelFile(modelId)
            val segments = WhisperEngine().transcribe(modelFile, samples)
            val text = segments.joinToString("\n") { it.text }.trim()
            require(text.isNotEmpty()) { "转写完成，但没有识别到阿拉伯语内容。" }

            history.upsert(
                existing.copy(
                    status = TaskStatus.COMPLETED,
                    updatedAt = System.currentTimeMillis(),
                    originalText = text,
                    errorMessage = "",
                ),
            )
            setStage(STAGE_COMPLETE, 100)
            Result.success(Data.Builder().putString(KEY_RECORD_ID, recordId).build())
        } catch (cancelled: CancellationException) {
            history.upsert(
                existing.copy(
                    status = TaskStatus.CANCELLED,
                    updatedAt = System.currentTimeMillis(),
                    errorMessage = "任务已取消",
                ),
            )
            throw cancelled
        } catch (error: Exception) {
            val message = error.message ?: "转写失败"
            history.upsert(
                existing.copy(
                    status = TaskStatus.FAILED,
                    updatedAt = System.currentTimeMillis(),
                    errorMessage = message,
                ),
            )
            Result.failure(Data.Builder().putString(KEY_ERROR, message).build())
        } finally {
            // Only the app-owned temporary copy is deleted. The user's source URI is never modified.
            taskDirectory.deleteRecursively()
        }
    }

    private suspend fun setStage(stage: String, progress: Int) {
        val recordId = inputData.getString(KEY_RECORD_ID).orEmpty()
        setForeground(
            WorkerNotifications.create(
                applicationContext,
                recordId.hashCode(),
                "阿语音频转写",
                stage,
                progress,
            ),
        )
        setProgress(
            Data.Builder()
                .putString(KEY_STAGE, stage)
                .putInt(KEY_PROGRESS, progress)
                .build(),
        )
    }

    companion object {
        const val KEY_RECORD_ID = "record_id"
        const val KEY_SOURCE_URI = "source_uri"
        const val KEY_SOURCE_NAME = "source_name"
        const val KEY_MODEL_ID = "model_id"
        const val KEY_STAGE = "stage"
        const val KEY_PROGRESS = "progress"
        const val KEY_ERROR = "error"
        const val STAGE_COPYING = "正在准备媒体"
        const val STAGE_DECODING = "正在解码音频"
        const val STAGE_TRANSCRIBING = "正在离线转写"
        const val STAGE_COMPLETE = "转写完成"
    }
}
