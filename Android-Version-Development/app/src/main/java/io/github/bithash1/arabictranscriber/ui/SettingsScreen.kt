package io.github.bithash1.arabictranscriber.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp

@Composable
fun SettingsScreen(
    state: MainUiState,
    onSave: (String, String, String, String) -> Unit,
) {
    var endpoint by remember(state.apiEndpoint) { mutableStateOf(state.apiEndpoint) }
    var model by remember(state.apiModel) { mutableStateOf(state.apiModel) }
    var apiKey by remember(state.apiKey) { mutableStateOf(state.apiKey) }
    var targetLanguage by remember(state.targetLanguage) { mutableStateOf(state.targetLanguage) }

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        SectionTitle("AI API")
        Text("这些设置只用于可选 AI 处理。本地转写不需要 API Key。")
        OutlinedTextField(
            value = endpoint,
            onValueChange = { endpoint = it },
            label = { Text("API 地址") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
        )
        OutlinedTextField(
            value = model,
            onValueChange = { model = it },
            label = { Text("API 模型") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = apiKey,
            onValueChange = { apiKey = it },
            label = { Text("API Key") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = targetLanguage,
            onValueChange = { targetLanguage = it },
            label = { Text("翻译目标语言") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Button(
            onClick = { onSave(endpoint, model, apiKey, targetLanguage) },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("保存 API 设置") }

        SectionTitle("模型存放位置")
        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainer)) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(state.modelDirectory, style = MaterialTheme.typography.bodySmall)
                Text("模型属于应用数据。卸载应用时系统可能同时删除模型，请在重新安装后检查下载状态。")
            }
        }

        SectionTitle("隐私与存储")
        Text("源媒体只读；应用创建的临时媒体在任务成功、失败或取消后删除。历史记录只保存文字、任务状态和必要元数据。")
        Text("AI 处理只发送你选择处理的转写文字，不发送音频或视频。API Key 使用 Android Keystore 加密。")
    }
}

