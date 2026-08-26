package io.github.bithash1.arabictranscriber.ai

import io.github.bithash1.arabictranscriber.model.AiOptions
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class AiResult(
    val correctedText: String,
    val translatedText: String,
    val diacritizedText: String,
    val inputTokens: Int,
    val outputTokens: Int,
)

class DeepSeekClient(
    private val endpoint: String,
    private val model: String,
    private val apiKey: String,
) {
    fun process(text: String, options: AiOptions, onProgress: (Int) -> Unit): AiResult {
        require(apiKey.isNotBlank()) { "请先在设置中填写 API Key。" }
        require(endpoint.startsWith("https://")) { "API 地址必须使用 HTTPS。" }
        val chunks = splitText(text)
        val corrected = mutableListOf<String>()
        val translated = mutableListOf<String>()
        val diacritized = mutableListOf<String>()
        var inputTokens = 0
        var outputTokens = 0

        chunks.forEachIndexed { index, chunk ->
            val response = requestChunk(chunk, options)
            if (options.correct) corrected += response.correctedText
            if (options.translate) translated += response.translatedText
            if (options.diacritize) diacritized += response.diacritizedText
            inputTokens += response.inputTokens
            outputTokens += response.outputTokens
            onProgress(((index + 1) * 100) / chunks.size)
        }
        return AiResult(
            correctedText = corrected.joinToString("\n\n"),
            translatedText = translated.joinToString("\n\n"),
            diacritizedText = diacritized.joinToString("\n\n"),
            inputTokens = inputTokens,
            outputTokens = outputTokens,
        )
    }

    private fun requestChunk(text: String, options: AiOptions): AiResult {
        val fields = buildList {
            if (options.correct) add("corrected_arabic")
            if (options.translate) add("translation")
            if (options.diacritize) add("diacritized_arabic")
        }
        val systemPrompt = """
            You process Arabic ASR transcripts. Return one JSON object only, with exactly these fields: ${fields.joinToString()}.
            Correct only clear recognition errors, incorrectly joined or separated words, spelling, and punctuation. Never summarize, add facts, or change meaning.
            When correction is requested, both translation and diacritization must use the corrected Arabic.
            Diacritization means adding accurate Arabic tashkeel without changing letters or wording.
            Translation target: ${options.targetLanguage}.
        """.trimIndent()
        val payload = JSONObject()
            .put("model", model)
            .put("temperature", 0.1)
            .put("response_format", JSONObject().put("type", "json_object"))
            .put(
                "messages",
                JSONArray()
                    .put(JSONObject().put("role", "system").put("content", systemPrompt))
                    .put(JSONObject().put("role", "user").put("content", text)),
            )

        val connection = (URL(endpoint).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 30_000
            readTimeout = 90_000
            doOutput = true
            setRequestProperty("Authorization", "Bearer $apiKey")
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
        }
        connection.outputStream.bufferedWriter(Charsets.UTF_8).use { it.write(payload.toString()) }
        val responseCode = connection.responseCode
        val body = (if (responseCode in 200..299) connection.inputStream else connection.errorStream)
            ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
        connection.disconnect()
        if (responseCode !in 200..299) {
            val detail = runCatching { JSONObject(body).optJSONObject("error")?.optString("message") }.getOrNull()
            error(detail?.takeIf { it.isNotBlank() } ?: "API 请求失败（HTTP $responseCode）")
        }

        val envelope = JSONObject(body)
        val content = envelope.getJSONArray("choices").getJSONObject(0)
            .getJSONObject("message").getString("content")
            .removePrefix("```json").removePrefix("```").removeSuffix("```").trim()
        val result = JSONObject(content)
        val usage = envelope.optJSONObject("usage")
        fun required(name: String, enabled: Boolean): String {
            if (!enabled) return ""
            return result.optString(name).trim().takeIf { it.isNotEmpty() }
                ?: error("AI 返回结果缺少 $name。")
        }
        return AiResult(
            correctedText = required("corrected_arabic", options.correct),
            translatedText = required("translation", options.translate),
            diacritizedText = required("diacritized_arabic", options.diacritize),
            inputTokens = usage?.optInt("prompt_tokens") ?: 0,
            outputTokens = usage?.optInt("completion_tokens") ?: 0,
        )
    }

    internal fun splitText(text: String, limit: Int = 5_500): List<String> {
        val paragraphs = text.split(Regex("\\n+"), limit = 0).map(String::trim).filter(String::isNotEmpty)
        if (paragraphs.isEmpty()) return listOf(text)
        val result = mutableListOf<String>()
        val current = StringBuilder()
        for (paragraph in paragraphs) {
            if (paragraph.length > limit) {
                if (current.isNotEmpty()) {
                    result += current.toString()
                    current.clear()
                }
                paragraph.chunked(limit).forEach(result::add)
            } else if (current.isNotEmpty() && current.length + paragraph.length + 1 > limit) {
                result += current.toString()
                current.clear()
                current.append(paragraph)
            } else {
                if (current.isNotEmpty()) current.append('\n')
                current.append(paragraph)
            }
        }
        if (current.isNotEmpty()) result += current.toString()
        return result
    }
}

