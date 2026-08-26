package io.github.bithash1.arabictranscriber.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextDirection
import androidx.compose.ui.unit.dp
import io.github.bithash1.arabictranscriber.model.TranscriptionRecord

private enum class ResultKind(val label: String) {
    ORIGINAL("原文"), CORRECTED("矫正"), DIACRITIZED("标音"), TRANSLATED("翻译"),
}

@Composable
fun ResultContent(
    record: TranscriptionRecord,
    onCopy: (String) -> Unit,
    onShare: (String) -> Unit,
    onExport: (String, String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val available = buildList {
        if (record.originalText.isNotBlank()) add(ResultKind.ORIGINAL)
        if (record.correctedText.isNotBlank()) add(ResultKind.CORRECTED)
        if (record.diacritizedText.isNotBlank()) add(ResultKind.DIACRITIZED)
        if (record.translatedText.isNotBlank()) add(ResultKind.TRANSLATED)
    }
    var selected by remember(record.id, available) { mutableStateOf(available.lastOrNull() ?: ResultKind.ORIGINAL) }
    val text = when (selected) {
        ResultKind.ORIGINAL -> record.originalText
        ResultKind.CORRECTED -> record.correctedText
        ResultKind.DIACRITIZED -> record.diacritizedText
        ResultKind.TRANSLATED -> record.translatedText
    }
    val stem = record.sourceName.substringBeforeLast('.').ifBlank { "transcript" }

    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (available.size > 1) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    available.forEach { kind ->
                        OutlinedButton(onClick = { selected = kind }, enabled = selected != kind) {
                            Text(kind.label)
                        }
                    }
                }
            }
            Text(
                text = text,
                modifier = Modifier.fillMaxWidth().widthIn(min = 200.dp)
                    .verticalScroll(rememberScrollState()),
                style = MaterialTheme.typography.bodyLarge.copy(textDirection = TextDirection.ContentOrRtl),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { onCopy(text) }) { Text("复制全文") }
                OutlinedButton(onClick = { onShare(text) }) { Text("分享") }
                OutlinedButton(onClick = { onExport("${stem}_${selected.name.lowercase()}.txt", text) }) {
                    Text("保存 TXT")
                }
            }
        }
    }
}

