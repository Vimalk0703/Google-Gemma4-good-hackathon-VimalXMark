/// Local assessment persistence using SharedPreferences.
///
/// Stores completed IMCI assessments so they survive app restarts.
/// Also stores the user's preferred language for multilingual support.
///
/// Storage format: JSON-serialized SavedAssessment objects.
/// Key pattern: "assessment_{timestamp_ms}" for assessments.
/// Key: "malaika_language" for language preference.
library;

import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

// ============================================================================
// Saved Assessment — serializable assessment result
// ============================================================================

class SavedAssessment {
  final String id;
  final DateTime timestamp;
  final int ageMonths;
  final double weightKg;
  final String severity; // "red", "yellow", "green"
  final Map<String, dynamic> findings;
  final Map<String, String> classifications; // step → classification label
  final String language;

  SavedAssessment({
    required this.id,
    required this.timestamp,
    required this.ageMonths,
    required this.weightKg,
    required this.severity,
    required this.findings,
    required this.classifications,
    this.language = 'en',
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'timestamp': timestamp.toIso8601String(),
        'ageMonths': ageMonths,
        'weightKg': weightKg,
        'severity': severity,
        'findings': findings,
        'classifications': classifications,
        'language': language,
      };

  factory SavedAssessment.fromJson(Map<String, dynamic> json) {
    return SavedAssessment(
      id: json['id'] as String,
      timestamp: DateTime.parse(json['timestamp'] as String),
      ageMonths: json['ageMonths'] as int,
      weightKg: (json['weightKg'] as num).toDouble(),
      severity: json['severity'] as String,
      findings: Map<String, dynamic>.from(json['findings'] as Map),
      classifications: Map<String, String>.from(json['classifications'] as Map),
      language: json['language'] as String? ?? 'en',
    );
  }
}

// ============================================================================
// Assessment Store — CRUD operations
// ============================================================================

class AssessmentStore {
  static const _keyPrefix = 'assessment_';
  static const _languageKey = 'malaika_language';

  /// Save a completed assessment.
  static Future<void> save(SavedAssessment assessment) async {
    final prefs = await SharedPreferences.getInstance();
    final json = jsonEncode(assessment.toJson());
    await prefs.setString('$_keyPrefix${assessment.id}', json);
  }

  /// Load all saved assessments, sorted newest first.
  static Future<List<SavedAssessment>> loadAll() async {
    final prefs = await SharedPreferences.getInstance();
    final keys = prefs.getKeys().where((k) => k.startsWith(_keyPrefix));
    final assessments = <SavedAssessment>[];

    for (final key in keys) {
      final json = prefs.getString(key);
      if (json == null) continue;
      try {
        final map = jsonDecode(json) as Map<String, dynamic>;
        assessments.add(SavedAssessment.fromJson(map));
      } catch (_) {
        // Skip corrupted entries silently
      }
    }

    assessments.sort((a, b) => b.timestamp.compareTo(a.timestamp));
    return assessments;
  }

  /// Load a single assessment by ID.
  static Future<SavedAssessment?> load(String id) async {
    final prefs = await SharedPreferences.getInstance();
    final json = prefs.getString('$_keyPrefix$id');
    if (json == null) return null;
    try {
      final map = jsonDecode(json) as Map<String, dynamic>;
      return SavedAssessment.fromJson(map);
    } catch (_) {
      return null;
    }
  }

  /// Delete a saved assessment.
  static Future<void> delete(String id) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('$_keyPrefix$id');
  }

  /// Get the number of saved assessments.
  static Future<int> count() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getKeys().where((k) => k.startsWith(_keyPrefix)).length;
  }

  // --------------------------------------------------------------------------
  // Language Preference
  // --------------------------------------------------------------------------

  /// Supported languages with display names.
  static const Map<String, String> supportedLanguages = {
    'en': 'English',
    'sw': 'Kiswahili',
    'fr': 'Fran\u00e7ais',
    'es': 'Espa\u00f1ol',
    'pt': 'Portugu\u00eas',
    'ha': 'Hausa',
    'am': '\u12A0\u121B\u122D\u129B', // Amharic
    'ar': '\u0627\u0644\u0639\u0631\u0628\u064A\u0629', // Arabic
    'hi': '\u0939\u093F\u0928\u094D\u0926\u0940', // Hindi
    'bn': '\u09AC\u09BE\u0982\u09B2\u09BE', // Bengali
  };

  /// Get the stored language preference (defaults to English).
  static Future<String> getLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_languageKey) ?? 'en';
  }

  /// Set the language preference.
  static Future<void> setLanguage(String languageCode) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_languageKey, languageCode);
  }

  /// Get the full language name for a code.
  static String languageName(String code) {
    return supportedLanguages[code] ?? code;
  }
}
