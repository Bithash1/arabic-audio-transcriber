package io.github.bithash1.arabictranscriber.model

import android.content.Context
import java.io.File
import java.io.FileInputStream

data class WhisperModelSpec(
    val id: String,
    val label: String,
    val recommended: Boolean,
    val url: String,
    val minimumValidBytes: Long,
)

class ModelManager(context: Context) {
    val modelDirectory: File = requireNotNull(context.getExternalFilesDir("models")) {
        "设备没有可用的应用存储空间。"
    }.apply { mkdirs() }

    fun spec(id: String): WhisperModelSpec = MODELS.firstOrNull { it.id == id }
        ?: error("不支持的模型：$id")

    fun modelFile(id: String): File = File(modelDirectory, "ggml-${spec(id).id}.bin")

    fun partialFile(id: String): File = File(modelDirectory, "ggml-${spec(id).id}.bin.part")

    fun availability(id: String): ModelAvailability {
        val file = modelFile(id)
        if (!file.exists()) return ModelAvailability.NOT_DOWNLOADED
        return if (isValidModelFile(file, spec(id))) {
            ModelAvailability.DOWNLOADED
        } else {
            ModelAvailability.DAMAGED
        }
    }

    fun uiStates(): List<ModelUiState> = MODELS.map {
        ModelUiState(it.id, it.label, it.recommended, availability(it.id))
    }

    fun isValidModelFile(file: File, spec: WhisperModelSpec): Boolean {
        if (!file.isFile || file.length() < spec.minimumValidBytes) return false
        return runCatching {
            val header = ByteArray(4)
            FileInputStream(file).use { input -> input.read(header) == header.size } &&
                header.contentEquals(byteArrayOf(0x6c, 0x6d, 0x67, 0x67)) // GGML_FILE_MAGIC, little-endian
        }.getOrDefault(false)
    }

    companion object {
        val MODELS = listOf(
            WhisperModelSpec(
                id = "small",
                label = "Small",
                recommended = false,
                url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin",
                minimumValidBytes = 400_000_000L,
            ),
            WhisperModelSpec(
                id = "medium",
                label = "Medium",
                recommended = true,
                url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin",
                minimumValidBytes = 1_300_000_000L,
            ),
            WhisperModelSpec(
                id = "large-v3",
                label = "Large v3",
                recommended = false,
                url = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin",
                minimumValidBytes = 2_800_000_000L,
            ),
        )
    }
}
