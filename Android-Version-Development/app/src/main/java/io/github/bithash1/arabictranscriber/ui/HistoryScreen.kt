package io.github.bithash1.arabictranscriber.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import io.github.bithash1.arabictranscriber.model.TaskStatus
import java.text.DateFormat
import java.util.Date

@Composable
fun HistoryScreen(
    state: MainUiState,
    onSelectRecord: (String) -> Unit,
    onDeleteRecord: (String) -> Unit,
    onCopy: (String) -> Unit,
    onShare: (String) -> Unit,
    onExport: (String, String) -> Unit,
) {
    if (state.history.isEmpty()) {
        Column(
            Modifier.fillMaxSize().padding(32.dp),
            verticalArrangement = Arrangement.Center,
        ) {
            Text("还没有转写记录", style = MaterialTheme.typography.headlineSmall)
            Text("完成一次转写后，文字结果会保存在这里；原始音频不会被保存。")
        }
        return
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        items(state.history, key = { it.id }) { record ->
            val selected = state.selectedRecordId == record.id
            Card(
                modifier = Modifier.fillMaxWidth().clickable { onSelectRecord(record.id) },
                colors = CardDefaults.cardColors(
                    containerColor = if (selected) MaterialTheme.colorScheme.secondaryContainer
                    else MaterialTheme.colorScheme.surfaceContainer,
                ),
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(record.sourceName, style = MaterialTheme.typography.titleMedium)
                    Text(
                        "${DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.SHORT).format(Date(record.updatedAt))} · ${record.modelId}",
                        style = MaterialTheme.typography.bodySmall,
                    )
                    Text(
                        when (record.status) {
                            TaskStatus.QUEUED -> "等待中"
                            TaskStatus.RUNNING -> "处理中"
                            TaskStatus.COMPLETED -> "已完成"
                            TaskStatus.FAILED -> "失败：${record.errorMessage}"
                            TaskStatus.CANCELLED -> "已取消"
                        },
                    )
                    if (selected && record.originalText.isNotBlank()) {
                        ResultContent(record, onCopy, onShare, onExport)
                    }
                    if (selected) {
                        Row(horizontalArrangement = Arrangement.End, modifier = Modifier.fillMaxWidth()) {
                            OutlinedButton(onClick = { onDeleteRecord(record.id) }) { Text("删除记录") }
                        }
                    }
                }
            }
        }
    }
}

