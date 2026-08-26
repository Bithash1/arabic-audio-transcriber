package io.github.bithash1.arabictranscriber.ui

import android.app.Application
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.work.Constraints
import androidx.work.Data
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkInfo
import androidx.work.WorkManager
import io.github.bithash1.arabictranscriber.TranscriberApplication
import io.github.bithash1.arabictranscriber.model.AiOptions
import io.github.bithash1.arabictranscriber.model.ModelAvailability
import io.github.bithash1.arabictranscriber.model.ModelUiState
import io.github.bithash1.arabictranscriber.model.TaskStatus
import io.github.bithash1.arabictranscriber.model.TranscriptionRecord
import io.github.bithash1.arabictranscriber.worker.AiProcessingWorker
import io.github.bithash1.arabictranscriber.worker.ModelDownloadWorker
import io.github.bithash1.arabictranscriber.worker.TranscriptionWorker
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.UUID

data class MainUiState(
    val selectedUri: Uri? = null,
    val selectedSourceName: String = "",
    val selectedModel: String = "medium",
    val models: List<ModelUiState> = emptyList(),
    val history: List<TranscriptionRecord> = emptyList(),
    val selectedRecordId: String? = null,
    val activeWorkId: UUID? = null,
    val taskStage: String = "",
    val taskProgress: Int = 0,
    val aiRunning: Boolean = false,
    val aiProgress: Int = 0,
    val errorMessage: String = "",
    val apiEndpoint: String = "",
    val apiModel: String = "",
    val apiKey: String = "",
    val targetLanguage: String = "简体中文",
    val modelDirectory: String = "",
) {
    val selectedRecord: TranscriptionRecord?
        get() = history.firstOrNull { it.id == selectedRecordId }
}

class MainViewModel(application: Application) : AndroidViewModel(application) {
    private val app = application as TranscriberApplication
    private val workManager = WorkManager.getInstance(application)
    private val _uiState = MutableStateFlow(
        MainUiState(
            selectedModel = app.preferences.selectedModel,
            models = app.modelManager.uiStates(),
            apiEndpoint = app.preferences.apiEndpoint,
            apiModel = app.preferences.apiModel,
            apiKey = app.apiKeyStore.load(),
            targetLanguage = app.preferences.targetLanguage,
            modelDirectory = app.modelManager.modelDirectory.absolutePath,
        ),
    )
    val uiState: StateFlow<MainUiState> = _uiState.asStateFlow()
    private var workObserver: Job? = null
    private var modelObserver: Job? = null
    private var activeChainName: String? = null

    init {
        refreshHistory()
        refreshModels()
    }

    fun selectMedia(uri: Uri, displayName: String) {
        _uiState.update {
            it.copy(selectedUri = uri, selectedSourceName = displayName, errorMessage = "")
        }
    }

    fun selectModel(id: String) {
        app.preferences.selectedModel = id
        _uiState.update { it.copy(selectedModel = id) }
    }

    fun startTranscription() {
        val state = _uiState.value
        val uri = state.selectedUri ?: return reportError("请先选择音频或视频文件。")
        val recordId = UUID.randomUUID().toString()
        val now = System.currentTimeMillis()
        app.historyStore.upsert(
            TranscriptionRecord(
                id = recordId,
                sourceName = state.selectedSourceName.ifBlank { "未命名音频" },
                modelId = state.selectedModel,
                createdAt = now,
                updatedAt = now,
                status = TaskStatus.QUEUED,
            ),
        )
        refreshHistory(recordId)

        val transcription = OneTimeWorkRequestBuilder<TranscriptionWorker>()
            .setInputData(
                Data.Builder()
                    .putString(TranscriptionWorker.KEY_RECORD_ID, recordId)
                    .putString(TranscriptionWorker.KEY_SOURCE_URI, uri.toString())
                    .putString(TranscriptionWorker.KEY_SOURCE_NAME, state.selectedSourceName)
                    .putString(TranscriptionWorker.KEY_MODEL_ID, state.selectedModel)
                    .build(),
            )
            .addTag("transcription")
            .build()

        if (app.modelManager.availability(state.selectedModel) == ModelAvailability.DOWNLOADED) {
            activeChainName = null
            workManager.enqueue(transcription)
        } else {
            val download = OneTimeWorkRequestBuilder<ModelDownloadWorker>()
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .setInputData(Data.Builder().putString(ModelDownloadWorker.KEY_MODEL_ID, state.selectedModel).build())
                .addTag("model-download-${state.selectedModel}")
                .build()
            val chainName = "download-and-transcribe-${state.selectedModel}"
            activeChainName = chainName
            workManager.beginUniqueWork(
                chainName,
                ExistingWorkPolicy.APPEND_OR_REPLACE,
                download,
            ).then(transcription).enqueue()
            observeModelDownload(download.id, state.selectedModel)
        }
        observeTranscription(transcription.id)
    }

    fun downloadModel(id: String) {
        val download = OneTimeWorkRequestBuilder<ModelDownloadWorker>()
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .setInputData(Data.Builder().putString(ModelDownloadWorker.KEY_MODEL_ID, id).build())
            .addTag("model-download-$id")
            .build()
        workManager.enqueueUniqueWork("model-download-$id", ExistingWorkPolicy.REPLACE, download)
        observeModelDownload(download.id, id)
    }

    fun cancelActiveTask() {
        val chainName = activeChainName
        if (chainName != null) workManager.cancelUniqueWork(chainName)
        else _uiState.value.activeWorkId?.let(workManager::cancelWorkById)
    }

    fun processWithAi(recordId: String, options: AiOptions) {
        if (!options.hasAnyTask) return reportError("请至少选择矫正、翻译或标音中的一项。")
        if (app.apiKeyStore.load().isBlank()) return reportError("请先在设置中填写 API Key。")
        val request = OneTimeWorkRequestBuilder<AiProcessingWorker>()
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .setInputData(
                Data.Builder()
                    .putString(AiProcessingWorker.KEY_RECORD_ID, recordId)
                    .putBoolean(AiProcessingWorker.KEY_CORRECT, options.correct)
                    .putBoolean(AiProcessingWorker.KEY_TRANSLATE, options.translate)
                    .putBoolean(AiProcessingWorker.KEY_DIACRITIZE, options.diacritize)
                    .putString(AiProcessingWorker.KEY_TARGET_LANGUAGE, options.targetLanguage)
                    .build(),
            )
            .addTag("ai-processing")
            .build()
        workManager.enqueue(request)
        _uiState.update { it.copy(aiRunning = true, aiProgress = 0, errorMessage = "") }
        viewModelScope.launch {
            workManager.getWorkInfoByIdFlow(request.id).catch { error -> reportError(error.message ?: "AI 任务状态异常") }
                .collect { info ->
                    info ?: return@collect
                    _uiState.update { it.copy(aiProgress = info.progress.getInt(AiProcessingWorker.KEY_PROGRESS, 0)) }
                    if (info.state.isFinished) {
                        activeChainName = null
                        refreshHistory(recordId)
                        _uiState.update {
                            it.copy(
                                aiRunning = false,
                                errorMessage = info.outputData.getString(AiProcessingWorker.KEY_ERROR).orEmpty(),
                            )
                        }
                        return@collect
                    }
                }
        }
    }

    fun selectRecord(id: String) {
        _uiState.update { it.copy(selectedRecordId = id, errorMessage = "") }
    }

    fun deleteRecord(id: String) {
        app.historyStore.delete(id)
        refreshHistory()
    }

    fun saveSettings(endpoint: String, model: String, key: String, targetLanguage: String) {
        if (!endpoint.startsWith("https://")) return reportError("API 地址必须以 https:// 开头。")
        app.preferences.apiEndpoint = endpoint
        app.preferences.apiModel = model
        app.preferences.targetLanguage = targetLanguage
        app.apiKeyStore.save(key)
        _uiState.update {
            it.copy(
                apiEndpoint = endpoint.trim(),
                apiModel = model.trim(),
                apiKey = key,
                targetLanguage = targetLanguage,
                errorMessage = "",
            )
        }
    }

    fun clearError() = _uiState.update { it.copy(errorMessage = "") }

    private fun observeTranscription(workId: UUID) {
        workObserver?.cancel()
        _uiState.update {
            it.copy(activeWorkId = workId, taskStage = "任务已加入队列", taskProgress = 0, errorMessage = "")
        }
        workObserver = viewModelScope.launch {
            workManager.getWorkInfoByIdFlow(workId).catch { error -> reportError(error.message ?: "任务状态异常") }
                .collect { info ->
                    info ?: return@collect
                    _uiState.update {
                        it.copy(
                            taskStage = info.progress.getString(TranscriptionWorker.KEY_STAGE)
                                ?: if (info.state == WorkInfo.State.ENQUEUED) "等待模型或系统资源" else it.taskStage,
                            taskProgress = info.progress.getInt(TranscriptionWorker.KEY_PROGRESS, it.taskProgress),
                        )
                    }
                    if (info.state.isFinished) {
                        refreshHistory()
                        _uiState.update {
                            it.copy(
                                activeWorkId = null,
                                taskStage = if (info.state == WorkInfo.State.SUCCEEDED) "转写完成" else "转写未完成",
                                taskProgress = if (info.state == WorkInfo.State.SUCCEEDED) 100 else it.taskProgress,
                                errorMessage = info.outputData.getString(TranscriptionWorker.KEY_ERROR).orEmpty(),
                            )
                        }
                    }
                }
        }
    }

    private fun observeModelDownload(workId: UUID, modelId: String) {
        modelObserver?.cancel()
        modelObserver = viewModelScope.launch {
            workManager.getWorkInfoByIdFlow(workId).collect { info ->
                info ?: return@collect
                val progress = info.progress.getInt(ModelDownloadWorker.KEY_PROGRESS, 0)
                _uiState.update { state ->
                    state.copy(
                        models = state.models.map { model ->
                            if (model.id == modelId && !info.state.isFinished) {
                                model.copy(availability = ModelAvailability.DOWNLOADING, progress = progress)
                            } else model
                        },
                    )
                }
                if (info.state.isFinished) {
                    refreshModels()
                    val error = info.outputData.getString(ModelDownloadWorker.KEY_ERROR).orEmpty()
                    if (error.isNotBlank()) reportError(error)
                }
            }
        }
    }

    private fun refreshHistory(selectId: String? = null) {
        viewModelScope.launch {
            val records = withContext(Dispatchers.IO) { app.historyStore.list() }
            _uiState.update { state ->
                val selection = selectId ?: state.selectedRecordId?.takeIf { id -> records.any { it.id == id } }
                    ?: records.firstOrNull()?.id
                state.copy(history = records, selectedRecordId = selection)
            }
        }
    }

    private fun refreshModels() {
        viewModelScope.launch(Dispatchers.IO) {
            val states = app.modelManager.uiStates()
            _uiState.update { it.copy(models = states) }
        }
    }

    private fun reportError(message: String) {
        _uiState.update { it.copy(errorMessage = message) }
    }
}
