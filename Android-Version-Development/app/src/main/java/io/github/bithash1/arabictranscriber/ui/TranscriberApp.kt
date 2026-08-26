package io.github.bithash1.arabictranscriber.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import io.github.bithash1.arabictranscriber.model.AiOptions

private enum class AppSection(val label: String, val symbol: String) {
    TRANSCRIBE("转写", "转"),
    HISTORY("记录", "记"),
    SETTINGS("设置", "设"),
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TranscriberApp(
    state: MainUiState,
    onPickMedia: () -> Unit,
    onSelectModel: (String) -> Unit,
    onDownloadModel: (String) -> Unit,
    onStartTranscription: () -> Unit,
    onCancelTranscription: () -> Unit,
    onSelectRecord: (String) -> Unit,
    onDeleteRecord: (String) -> Unit,
    onProcessAi: (String, AiOptions) -> Unit,
    onSaveSettings: (String, String, String, String) -> Unit,
    onClearError: () -> Unit,
    onCopy: (String) -> Unit,
    onShare: (String) -> Unit,
    onExport: (String, String) -> Unit,
) {
    var section by rememberSaveable { mutableStateOf(AppSection.TRANSCRIBE) }
    Scaffold(
        contentWindowInsets = WindowInsets.safeDrawing,
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        when (section) {
                            AppSection.TRANSCRIBE -> "阿语音频转写"
                            AppSection.HISTORY -> "转写记录"
                            AppSection.SETTINGS -> "设置"
                        },
                    )
                },
            )
        },
        bottomBar = {
            NavigationBar {
                AppSection.entries.forEach { item ->
                    NavigationBarItem(
                        selected = section == item,
                        onClick = { section = item },
                        icon = { Text(item.symbol) },
                        label = { Text(item.label) },
                    )
                }
            }
        },
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when (section) {
                AppSection.TRANSCRIBE -> HomeScreen(
                    state = state,
                    onPickMedia = onPickMedia,
                    onSelectModel = onSelectModel,
                    onDownloadModel = onDownloadModel,
                    onStartTranscription = onStartTranscription,
                    onCancelTranscription = onCancelTranscription,
                    onProcessAi = onProcessAi,
                    onCopy = onCopy,
                    onShare = onShare,
                    onExport = onExport,
                )
                AppSection.HISTORY -> HistoryScreen(
                    state = state,
                    onSelectRecord = onSelectRecord,
                    onDeleteRecord = onDeleteRecord,
                    onCopy = onCopy,
                    onShare = onShare,
                    onExport = onExport,
                )
                AppSection.SETTINGS -> SettingsScreen(state, onSaveSettings)
            }
        }
    }

    if (state.errorMessage.isNotBlank()) {
        AlertDialog(
            onDismissRequest = onClearError,
            confirmButton = { TextButton(onClick = onClearError) { Text("知道了") } },
            title = { Text("操作未完成") },
            text = { Text(state.errorMessage) },
        )
    }
}
