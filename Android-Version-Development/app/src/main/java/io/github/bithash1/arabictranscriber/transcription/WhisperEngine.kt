package io.github.bithash1.arabictranscriber.transcription

import io.github.bithash1.arabictranscriber.model.TranscriptSegment
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import java.io.File

class WhisperEngine {
    suspend fun transcribe(model: File, samples: FloatArray): List<TranscriptSegment> =
        withContext(Dispatchers.Default) {
            require(model.isFile) { "模型未下载或已经被删除。" }
            val threads = Runtime.getRuntime().availableProcessors().coerceIn(2, 8)
            val json = NativeWhisperBridge.transcribe(model.absolutePath, samples, "ar", threads)
            val array = JSONArray(json)
            buildList(array.length()) {
                repeat(array.length()) { index ->
                    val item = array.getJSONObject(index)
                    val text = item.getString("text").trim()
                    if (text.isNotEmpty()) {
                        add(
                            TranscriptSegment(
                                startMs = item.getLong("start_ms"),
                                endMs = item.getLong("end_ms"),
                                text = text,
                            ),
                        )
                    }
                }
            }
        }
}

object NativeWhisperBridge {
    init {
        System.loadLibrary("whisper_jni")
    }

    external fun transcribe(
        modelPath: String,
        samples: FloatArray,
        language: String,
        threads: Int,
    ): String
}

