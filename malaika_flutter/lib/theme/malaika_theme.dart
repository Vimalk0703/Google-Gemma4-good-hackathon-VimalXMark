/// Malaika dark theme — matches the web UI (static/index.html).
library;

import 'package:flutter/material.dart';

/// Color constants matching the CSS variables in index.html.
class MalaikaColors {
  static const primary = Color(0xFF4FC3F7);     // --pri
  static const background = Color(0xFF0A1628);   // --bg
  static const surface = Color(0xFF132039);       // --sf
  static const text = Color(0xFFE0E6ED);          // --tx
  static const textMuted = Color(0xFF7B8FA3);     // --txm
  static const userBubble = Color(0xFF1E88E5);    // --ubbl
  static const botBubble = Color(0xFF132039);      // --bbbl
  static const green = Color(0xFF66BB6A);          // --grn
  static const yellow = Color(0xFFFFCA28);         // --ylw
  static const red = Color(0xFFEF5350);            // --red

  /// Get severity color.
  static Color forSeverity(String severity) {
    switch (severity) {
      case 'red':
        return red;
      case 'yellow':
        return yellow;
      case 'green':
        return green;
      default:
        return textMuted;
    }
  }

  /// Get severity background (transparent tint).
  static Color forSeverityBackground(String severity) {
    switch (severity) {
      case 'red':
        return red.withOpacity(0.08);
      case 'yellow':
        return yellow.withOpacity(0.06);
      case 'green':
        return green.withOpacity(0.06);
      default:
        return Colors.transparent;
    }
  }

  /// Get severity badge label.
  static String severityLabel(String severity) {
    switch (severity) {
      case 'red':
        return 'URGENT';
      case 'yellow':
        return 'CAUTION';
      case 'green':
        return 'CLEAR';
      default:
        return severity.toUpperCase();
    }
  }
}

/// Malaika app theme data.
ThemeData malaikaTheme() {
  return ThemeData.dark().copyWith(
    scaffoldBackgroundColor: MalaikaColors.background,
    colorScheme: const ColorScheme.dark(
      primary: MalaikaColors.primary,
      surface: MalaikaColors.surface,
      error: MalaikaColors.red,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: MalaikaColors.background,
      foregroundColor: MalaikaColors.primary,
      elevation: 0,
      centerTitle: true,
    ),
    textTheme: const TextTheme(
      bodyLarge: TextStyle(color: MalaikaColors.text),
      bodyMedium: TextStyle(color: MalaikaColors.text),
      bodySmall: TextStyle(color: MalaikaColors.textMuted),
      titleMedium: TextStyle(color: MalaikaColors.primary, fontWeight: FontWeight.w600),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: MalaikaColors.background,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: Colors.white.withOpacity(0.08)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: MalaikaColors.primary),
      ),
      hintStyle: const TextStyle(color: MalaikaColors.textMuted),
    ),
  );
}
