package io.github.bithash1.arabictranscriber.model

enum class TaskStatus { QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED }

data class TranscriptSegment(
    val startMs: Long,
    val endMs: Long,
    val text: String,
)

data class TranscriptionRecord(
    val id: String,
    val sourceName: String,
    val modelId: String,
    val createdAt: Long,
    val updatedAt: Long,
    val status: TaskStatus,
    val originalText: String = "",
    val correctedText: String = "",
    val translatedText: String = "",
    val diacritizedText: String = "",
    val errorMessage: String = "",
    val inputTokens: Int = 0,
    val outputTokens: Int = 0,
) {
    val preferredArabic: String
        get() = diacritizedText.ifBlank { correctedText.ifBlank { originalText } }
}

data class AiOptions(
    val correct: Boolean,
    val translate: Boolean,
    val diacritize: Boolean,
    val targetLanguage: String,
) {
    val hasAnyTask: Boolean get() = correct || translate || diacritize
}

enum class ModelAvailability { CHECKING, NOT_DOWNLOADED, DOWNLOADING, DOWNLOADED, DAMAGED }

data class ModelUiState(
    val id: String,
    val label: String,
    val recommended: Boolean,
    val availability: ModelAvailability,
    val progress: Int = 0,
)

