/// Malaika light theme — clean, medical, WHO-aligned.
///
/// Color palette: WHO blue primary, slate neutrals, traffic-light severity.
/// Designed for clinical trust and readability.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Color constants for the Malaika design system.
class MalaikaColors {
  MalaikaColors._();

  // --- Brand ---
  static const primary = Color(0xFF0072BC); // WHO blue
  static const primaryLight = Color(0xFFE8F4FD);
  static const primaryDark = Color(0xFF005A96);
  static const accent = Color(0xFF00897B); // Teal — health, calm

  // --- Backgrounds ---
  static const background = Color(0xFFF8FAFC); // Slate-50
  static const surface = Color(0xFFFFFFFF);
  static const surfaceAlt = Color(0xFFF1F5F9); // Slate-100

  // --- Text ---
  static const text = Color(0xFF1E293B); // Slate-800
  static const textSecondary = Color(0xFF475569); // Slate-600
  static const textMuted = Color(0xFF94A3B8); // Slate-400

  // --- Chat ---
  static const userBubble = Color(0xFF0072BC);
  static const botBubble = Color(0xFFF1F5F9);

  // --- WHO Severity Traffic Light ---
  static const green = Color(0xFF059669); // Emerald-600
  static const greenLight = Color(0xFFECFDF5);
  static const yellow = Color(0xFFD97706); // Amber-600
  static const yellowLight = Color(0xFFFFFBEB);
  static const red = Color(0xFFDC2626); // Red-600
  static const redLight = Color(0xFFFEF2F2);

  // --- Borders ---
  static const border = Color(0xFFE2E8F0); // Slate-200
  static const borderLight = Color(0xFFF1F5F9);

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

  /// Get severity background.
  static Color forSeverityBackground(String severity) {
    switch (severity) {
      case 'red':
        return redLight;
      case 'yellow':
        return yellowLight;
      case 'green':
        return greenLight;
      default:
        return Colors.transparent;
    }
  }

  /// Get severity badge label.
  static String severityLabel(String severity) {
    switch (severity) {
      case 'red':
        return 'URGENT REFERRAL';
      case 'yellow':
        return 'CAUTION';
      case 'green':
        return 'CLEAR';
      default:
        return severity.toUpperCase();
    }
  }

  /// Get severity icon.
  static IconData severityIcon(String severity) {
    switch (severity) {
      case 'red':
        return Icons.warning_rounded;
      case 'yellow':
        return Icons.info_rounded;
      case 'green':
        return Icons.check_circle_rounded;
      default:
        return Icons.help_outline_rounded;
    }
  }
}

/// Malaika app theme — light, clean, medical.
ThemeData malaikaTheme() {
  return ThemeData.light().copyWith(
    scaffoldBackgroundColor: MalaikaColors.background,
    colorScheme: const ColorScheme.light(
      primary: MalaikaColors.primary,
      surface: MalaikaColors.surface,
      error: MalaikaColors.red,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: MalaikaColors.surface,
      foregroundColor: MalaikaColors.text,
      elevation: 0,
      centerTitle: true,
      surfaceTintColor: Colors.transparent,
      systemOverlayStyle: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.dark,
        statusBarBrightness: Brightness.light,
      ),
    ),
    textTheme: const TextTheme(
      bodyLarge: TextStyle(color: MalaikaColors.text),
      bodyMedium: TextStyle(color: MalaikaColors.text),
      bodySmall: TextStyle(color: MalaikaColors.textMuted),
      titleMedium: TextStyle(
          color: MalaikaColors.text, fontWeight: FontWeight.w600),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: MalaikaColors.surfaceAlt,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(24),
        borderSide: const BorderSide(color: MalaikaColors.border),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(24),
        borderSide: const BorderSide(color: MalaikaColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(24),
        borderSide:
            const BorderSide(color: MalaikaColors.primary, width: 1.5),
      ),
      hintStyle: const TextStyle(color: MalaikaColors.textMuted, fontSize: 14),
      contentPadding:
          const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
    ),
    cardTheme: CardThemeData(
      color: MalaikaColors.surface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: MalaikaColors.border),
      ),
    ),
    dividerColor: MalaikaColors.border,
  );
}
