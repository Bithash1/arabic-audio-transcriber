package io.github.bithash1.arabictranscriber.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import io.github.bithash1.arabictranscriber.model.AiOptions
import io.github.bithash1.arabictranscriber.model.ModelAvailability
import io.github.bithash1.arabictranscriber.model.ModelUiState
import io.github.bithash1.arabictranscriber.model.TaskStatus

@Composable
fun HomeScreen(
    state: MainUiState,
    onPickMedia: () -> Unit,
    onSelectModel: (String) -> Unit,
    onDownloadModel: (String) -> Unit,
    onStartTranscription: () -> Unit,
    onCancelTranscription: () -> Unit,
    onProcessAi: (String, AiOptions) -> Unit,
    onCopy: (String) -> Unit,
    onShare: (String) -> Unit,
    onExport: (String, String) -> Unit,
) {
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        PrivacyCard()
        SectionTitle("1. 选择媒体")
        OutlinedButton(onClick = onPickMedia, modifier = Modifier.fillMaxWidth()) {
            Text(if (state.selectedSourceName.isBlank()) "选择音频或视频" else state.selectedSourceName)
        }

        SectionTitle("2. 选择离线模型")
        state.models.forEach { model ->
            ModelCard(
                model = model,
                selected = state.selectedModel == model.id,
                onSelect = { onSelectModel(model.id) },
                onDownload = { onDownloadModel(model.id) },
            )
        }

        Button(
            onClick = onStartTranscription,
            modifier = Modifier.fillMaxWidth(),
            enabled = state.selectedUri != null && state.activeWorkId == null,
        ) {
            Text("开始本地转写")
        }
        if (state.activeWorkId != null) {
            TaskProgress(state.taskStage, state.taskProgress)
            OutlinedButton(onClick = onCancelTranscription, modifier = Modifier.fillMaxWidth()) { Text("取消任务") }
        } else if (state.taskStage.isNotBlank()) {
            Text(state.taskStage, color = MaterialTheme.colorScheme.primary)
        }

        val record = state.selectedRecord
        if (record != null && record.status == TaskStatus.COMPLETED && record.originalText.isNotBlank()) {
            SectionTitle("转写结果")
            ResultContent(record, onCopy, onShare, onExport)
            AiPanel(state, record.id, onProcessAi)
        }
    }
}

@Composable
private fun PrivacyCard() {
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("媒体始终留在本机", style = MaterialTheme.typography.titleMedium)
            Text("应用只读取你选择的源文件。转写结束、失败或取消后，应用创建的临时副本会自动删除。")
        }
    }
}

@Composable
private fun ModelCard(
    model: ModelUiState,
    selected: Boolean,
    onSelect: () -> Unit,
    onDownload: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onSelect),
        colors = CardDefaults.cardColors(
            containerColor = if (selected) MaterialTheme.colorScheme.secondaryContainer
            else MaterialTheme.colorScheme.surfaceContainer,
        ),
    ) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                RadioButton(selected = selected, onClick = onSelect)
                Column(Modifier.weight(1f)) {
                    Text(
                        model.label + if (model.recommended) " · 推荐" else "",
                        style = MaterialTheme.typography.titleMedium,
                    )
                    Text(
                        when (model.availability) {
                            ModelAvailability.CHECKING -> "正在检查"
                            ModelAvailability.NOT_DOWNLOADED -> "未下载"
                            ModelAvailability.DOWNLOADING -> "正在下载 ${model.progress}%"
                            ModelAvailability.DOWNLOADED -> "已下载"
                            ModelAvailability.DAMAGED -> "文件不完整，需要重新下载"
                        },
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
                if (model.availability == ModelAvailability.NOT_DOWNLOADED ||
                    model.availability == ModelAvailability.DAMAGED
                ) {
                    OutlinedButton(onClick = onDownload) { Text("下载") }
                }
            }
            if (model.availability == ModelAvailability.DOWNLOADING) {
                LinearProgressIndicator(
                    progress = { model.progress / 100f },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun TaskProgress(stage: String, progress: Int) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(stage.ifBlank { "处理中" })
            Text("$progress%")
        }
        LinearProgressIndicator(progress = { progress / 100f }, modifier = Modifier.fillMaxWidth())
    }
}

@Composable
private fun AiPanel(state: MainUiState, recordId: String, onProcessAi: (String, AiOptions) -> Unit) {
    var correct by rememberSaveable(recordId) { mutableStateOf(false) }
    var translate by rememberSaveable(recordId) { mutableStateOf(false) }
    var diacritize by rememberSaveable(recordId) { mutableStateOf(false) }
    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerHigh)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("3. 可选 AI 处理", style = MaterialTheme.typography.titleLarge)
            Text("本步骤与转写完全分离。只有转写文字会发送到 API，媒体不会上传。")
            OptionRow("矫正明显识别错误", correct) { correct = it }
            OptionRow("翻译为 ${state.targetLanguage}", translate) { translate = it }
            OptionRow("添加阿语标音", diacritize) { diacritize = it }
            Button(
                onClick = {
                    onProcessAi(
                        recordId,
                        AiOptions(correct, translate, diacritize, state.targetLanguage),
                    )
                },
                enabled = !state.aiRunning && (correct || translate || diacritize),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (state.aiRunning) "AI 处理中 ${state.aiProgress}%" else "开始 AI 处理")
            }
            if (state.aiRunning) {
                LinearProgressIndicator(progress = { state.aiProgress / 100f }, modifier = Modifier.fillMaxWidth())
            }
        }
    }
}

@Composable
private fun OptionRow(label: String, checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Checkbox(checked = checked, onCheckedChange = onCheckedChange)
        Text(label, modifier = Modifier.clickable { onCheckedChange(!checked) })
    }
}

@Composable
internal fun SectionTitle(text: String) {
    Text(text, style = MaterialTheme.typography.titleLarge)
}
