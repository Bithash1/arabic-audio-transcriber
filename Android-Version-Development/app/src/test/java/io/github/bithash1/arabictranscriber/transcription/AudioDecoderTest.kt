package io.github.bithash1.arabictranscriber.transcription

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test

class AudioDecoderTest {
    @Test
    fun resampleKeepsSamplesWhenRateMatches() {
        val input = floatArrayOf(-1f, 0f, 1f)
        assertArrayEquals(input, AudioDecoder().resample(input, 16_000, 16_000), 0f)
    }

    @Test
    fun resampleConvertsFortyEightKhzToSixteenKhz() {
        val input = FloatArray(48) { it.toFloat() / 48f }
        val output = AudioDecoder().resample(input, 48_000, 16_000)
        assertEquals(16, output.size)
        assertEquals(input.first(), output.first(), 0.0001f)
    }
}

