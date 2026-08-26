package io.github.bithash1.arabictranscriber.data

import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import io.github.bithash1.arabictranscriber.model.TaskStatus
import io.github.bithash1.arabictranscriber.model.TranscriptionRecord

class HistoryStore(context: Context) : SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """
            CREATE TABLE transcripts (
                id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                model_id TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL,
                status TEXT NOT NULL,
                original_text TEXT NOT NULL DEFAULT '',
                corrected_text TEXT NOT NULL DEFAULT '',
                translated_text TEXT NOT NULL DEFAULT '',
                diacritized_text TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0
            )
            """.trimIndent(),
        )
        db.execSQL("CREATE INDEX transcripts_updated_at ON transcripts(updated_at DESC)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) = Unit

    @Synchronized
    fun upsert(record: TranscriptionRecord) {
        writableDatabase.insertWithOnConflict(
            "transcripts",
            null,
            record.toValues(),
            SQLiteDatabase.CONFLICT_REPLACE,
        )
    }

    @Synchronized
    fun get(id: String): TranscriptionRecord? = readableDatabase.query(
        "transcripts",
        COLUMNS,
        "id = ?",
        arrayOf(id),
        null,
        null,
        null,
        "1",
    ).use { cursor -> if (cursor.moveToFirst()) cursor.toRecord() else null }

    @Synchronized
    fun list(): List<TranscriptionRecord> = readableDatabase.query(
        "transcripts",
        COLUMNS,
        null,
        null,
        null,
        null,
        "updated_at DESC",
    ).use { cursor -> buildList { while (cursor.moveToNext()) add(cursor.toRecord()) } }

    @Synchronized
    fun delete(id: String) {
        writableDatabase.delete("transcripts", "id = ?", arrayOf(id))
    }

    private fun TranscriptionRecord.toValues() = ContentValues().apply {
        put("id", id)
        put("source_name", sourceName)
        put("model_id", modelId)
        put("created_at", createdAt)
        put("updated_at", updatedAt)
        put("status", status.name)
        put("original_text", originalText)
        put("corrected_text", correctedText)
        put("translated_text", translatedText)
        put("diacritized_text", diacritizedText)
        put("error_message", errorMessage)
        put("input_tokens", inputTokens)
        put("output_tokens", outputTokens)
    }

    private fun Cursor.toRecord() = TranscriptionRecord(
        id = getString(getColumnIndexOrThrow("id")),
        sourceName = getString(getColumnIndexOrThrow("source_name")),
        modelId = getString(getColumnIndexOrThrow("model_id")),
        createdAt = getLong(getColumnIndexOrThrow("created_at")),
        updatedAt = getLong(getColumnIndexOrThrow("updated_at")),
        status = TaskStatus.valueOf(getString(getColumnIndexOrThrow("status"))),
        originalText = getString(getColumnIndexOrThrow("original_text")),
        correctedText = getString(getColumnIndexOrThrow("corrected_text")),
        translatedText = getString(getColumnIndexOrThrow("translated_text")),
        diacritizedText = getString(getColumnIndexOrThrow("diacritized_text")),
        errorMessage = getString(getColumnIndexOrThrow("error_message")),
        inputTokens = getInt(getColumnIndexOrThrow("input_tokens")),
        outputTokens = getInt(getColumnIndexOrThrow("output_tokens")),
    )

    companion object {
        private const val DATABASE_NAME = "transcriptions.db"
        private const val DATABASE_VERSION = 1
        private val COLUMNS = arrayOf(
            "id", "source_name", "model_id", "created_at", "updated_at", "status",
            "original_text", "corrected_text", "translated_text", "diacritized_text",
            "error_message", "input_tokens", "output_tokens",
        )
    }
}

