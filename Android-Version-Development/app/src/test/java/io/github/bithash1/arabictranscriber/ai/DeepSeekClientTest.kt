package io.github.bithash1.arabictranscriber.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DeepSeekClientTest {
    private val client = DeepSeekClient("https://example.com", "test", "key")

    @Test
    fun splitTextPreservesParagraphOrder() {
        val chunks = client.splitText("الأول\nالثاني\nالثالث", limit = 12)
        assertEquals("الأول\nالثاني\nالثالث", chunks.joinToString("\n"))
        assertTrue(chunks.all { it.length <= 12 })
    }

    @Test
    fun splitTextCutsSingleLongParagraph() {
        val chunks = client.splitText("abcdefghij", limit = 4)
        assertEquals(listOf("abcd", "efgh", "ij"), chunks)
    }
}

