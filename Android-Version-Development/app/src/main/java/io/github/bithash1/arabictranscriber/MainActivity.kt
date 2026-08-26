package io.github.bithash1.arabictranscriber

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.content.pm.PackageManager
import android.provider.OpenableColumns
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import io.github.bithash1.arabictranscriber.ui.MainViewModel
import io.github.bithash1.arabictranscriber.ui.TranscriberApp
import io.github.bithash1.arabictranscriber.ui.theme.ArabicTranscriberTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val viewModel: MainViewModel = viewModel()
            val state by viewModel.uiState.collectAsStateWithLifecycle()
            var pendingExportText by remember { mutableStateOf("") }

            val mediaPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
                if (uri != null) {
                    runCatching {
                        contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    }
                    viewModel.selectMedia(uri, displayName(uri))
                }
            }
            val textExporter = rememberLauncherForActivityResult(
                ActivityResultContracts.CreateDocument("text/plain"),
            ) { uri ->
                if (uri != null) {
                    contentResolver.openOutputStream(uri)?.bufferedWriter(Charsets.UTF_8)?.use {
                        it.write(pendingExportText)
                    }
                }
            }
            val notificationPermission = rememberLauncherForActivityResult(
                ActivityResultContracts.RequestPermission(),
            ) { }
            fun ensureNotificationPermission() {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                    checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
                ) {
                    notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
                }
            }

            LaunchedEffect(Unit) {
                sharedMediaUri(intent)?.let { uri ->
                    runCatching {
                        contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    }
                    viewModel.selectMedia(uri, displayName(uri))
                }
            }

            ArabicTranscriberTheme {
                TranscriberApp(
                    state = state,
                    onPickMedia = { mediaPicker.launch(arrayOf("audio/*", "video/*")) },
                    onSelectModel = viewModel::selectModel,
                    onDownloadModel = { modelId ->
                        ensureNotificationPermission()
                        viewModel.downloadModel(modelId)
                    },
                    onStartTranscription = {
                        ensureNotificationPermission()
                        viewModel.startTranscription()
                    },
                    onCancelTranscription = viewModel::cancelActiveTask,
                    onSelectRecord = viewModel::selectRecord,
                    onDeleteRecord = viewModel::deleteRecord,
                    onProcessAi = viewModel::processWithAi,
                    onSaveSettings = viewModel::saveSettings,
                    onClearError = viewModel::clearError,
                    onCopy = { copyText(it) },
                    onShare = { shareText(it) },
                    onExport = { filename, text ->
                        pendingExportText = text
                        textExporter.launch(filename)
                    },
                )
            }
        }
    }

    private fun displayName(uri: Uri): String {
        return contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) cursor.getString(0) else null
        } ?: uri.lastPathSegment ?: "未命名音频"
    }

    @Suppress("DEPRECATION")
    private fun sharedMediaUri(intent: Intent): Uri? {
        if (intent.action != Intent.ACTION_SEND) return null
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
        } else {
            intent.getParcelableExtra(Intent.EXTRA_STREAM)
        }
    }

    private fun copyText(text: String) {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("转写文本", text))
    }

    private fun shareText(text: String) {
        startActivity(
            Intent.createChooser(
                Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_TEXT, text)
                },
                "分享文本",
            ),
        )
    }
}
