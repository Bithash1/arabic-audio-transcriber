package io.github.bithash1.arabictranscriber

import android.app.Application
import io.github.bithash1.arabictranscriber.data.ApiKeyStore
import io.github.bithash1.arabictranscriber.data.AppPreferences
import io.github.bithash1.arabictranscriber.data.HistoryStore
import io.github.bithash1.arabictranscriber.model.ModelManager

class TranscriberApplication : Application() {
    val historyStore by lazy { HistoryStore(this) }
    val preferences by lazy { AppPreferences(this) }
    val apiKeyStore by lazy { ApiKeyStore(this) }
    val modelManager by lazy { ModelManager(this) }
}

