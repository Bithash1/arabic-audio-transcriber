package io.github.bithash1.arabictranscriber.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF2D675B),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFB0F0DE),
    onPrimaryContainer = Color(0xFF00201A),
    secondary = Color(0xFF4B635D),
    tertiary = Color(0xFF426277),
    background = Color(0xFFF7F6FA),
    surface = Color(0xFFF7F6FA),
    surfaceVariant = Color(0xFFDCE5E1),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF95D4C3),
    primaryContainer = Color(0xFF0F4F43),
    secondary = Color(0xFFB2CCC4),
    tertiary = Color(0xFFA9CCE5),
)

@Composable
fun ArabicTranscriberTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
        content = content,
    )
}

