package io.github.bithash1.arabictranscriber.worker

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.WorkerParameters
import io.github.bithash1.arabictranscriber.TranscriberApplication
import io.github.bithash1.arabictranscriber.ai.DeepSeekClient
import io.github.bithash1.arabictranscriber.model.AiOptions
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class AiProcessingWorker(
    appContext: Context,
    params: WorkerParameters,
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val recordId = inputData.getString(KEY_RECORD_ID) ?: return@withContext Result.failure()
        val app = applicationContext as TranscriberApplication
        val record = app.historyStore.get(recordId) ?: return@withContext Result.failure()
        val options = AiOptions(
            correct = inputData.getBoolean(KEY_CORRECT, false),
            translate = inputData.getBoolean(KEY_TRANSLATE, false),
            diacritize = inputData.getBoolean(KEY_DIACRITIZE, false),
            targetLanguage = inputData.getString(KEY_TARGET_LANGUAGE) ?: app.preferences.targetLanguage,
        )
        if (!options.hasAnyTask) return@withContext Result.failure(errorData("请至少选择一种 AI 处理。"))
        try {
            setForeground(
                WorkerNotifications.create(
                    applicationContext,
                    recordId.hashCode(),
                    "正在进行 AI 文字处理",
                    "只发送转写文字，不上传媒体",
                    null,
                ),
            )
            val client = DeepSeekClient(
                endpoint = app.preferences.apiEndpoint,
                model = app.preferences.apiModel,
                apiKey = app.apiKeyStore.load(),
            )
            val source = if (options.correct) record.originalText else record.correctedText.ifBlank { record.originalText }
            val result = client.process(source, options) { progress ->
                setProgressAsync(Data.Builder().putInt(KEY_PROGRESS, progress).build())
            }
            app.historyStore.upsert(
                record.copy(
                    updatedAt = System.currentTimeMillis(),
                    correctedText = if (options.correct) result.correctedText else record.correctedText,
                    translatedText = if (options.translate) result.translatedText else record.translatedText,
                    diacritizedText = if (options.diacritize) result.diacritizedText else record.diacritizedText,
                    errorMessage = "",
                    inputTokens = record.inputTokens + result.inputTokens,
                    outputTokens = record.outputTokens + result.outputTokens,
                ),
            )
            Result.success(Data.Builder().putString(KEY_RECORD_ID, recordId).build())
        } catch (error: Exception) {
            Result.failure(errorData(error.message ?: "AI 处理失败"))
        }
    }

    private fun errorData(message: String) = Data.Builder().putString(KEY_ERROR, message).build()

    companion object {
        const val KEY_RECORD_ID = "record_id"
        const val KEY_CORRECT = "correct"
        const val KEY_TRANSLATE = "translate"
        const val KEY_DIACRITIZE = "diacritize"
        const val KEY_TARGET_LANGUAGE = "target_language"
        const val KEY_PROGRESS = "progress"
        const val KEY_ERROR = "error"
    }
}
