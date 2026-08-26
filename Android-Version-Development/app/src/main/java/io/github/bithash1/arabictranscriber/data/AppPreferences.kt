package io.github.bithash1.arabictranscriber.data

import android.content.Context
import androidx.core.content.edit

class AppPreferences(context: Context) {
    private val preferences = context.getSharedPreferences("app_preferences", Context.MODE_PRIVATE)

    var apiEndpoint: String
        get() = preferences.getString(KEY_ENDPOINT, DEFAULT_ENDPOINT) ?: DEFAULT_ENDPOINT
        set(value) = preferences.edit { putString(KEY_ENDPOINT, value.trim()) }

    var apiModel: String
        get() = preferences.getString(KEY_API_MODEL, DEFAULT_API_MODEL) ?: DEFAULT_API_MODEL
        set(value) = preferences.edit { putString(KEY_API_MODEL, value.trim()) }

    var targetLanguage: String
        get() = preferences.getString(KEY_TARGET_LANGUAGE, "简体中文") ?: "简体中文"
        set(value) = preferences.edit { putString(KEY_TARGET_LANGUAGE, value) }

    var selectedModel: String
        get() = preferences.getString(KEY_SELECTED_MODEL, "medium") ?: "medium"
        set(value) = preferences.edit { putString(KEY_SELECTED_MODEL, value) }

    companion object {
        const val DEFAULT_ENDPOINT = "https://api.deepseek.com/chat/completions"
        const val DEFAULT_API_MODEL = "deepseek-chat"
        private const val KEY_ENDPOINT = "api_endpoint"
        private const val KEY_API_MODEL = "api_model"
        private const val KEY_TARGET_LANGUAGE = "target_language"
        private const val KEY_SELECTED_MODEL = "selected_model"
    }
}
