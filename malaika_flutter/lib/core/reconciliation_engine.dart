/// Malaika Reconciliation Engine — cross-references Q&A and vision findings.
///
/// After the questionnaire (verbal history) and camera monitoring (visual
/// examination), this engine compares both data sources to:
/// 1. Detect conflicts (Q&A says OK but vision sees a problem, or vice versa)
/// 2. Generate warnings with specific recommendations
/// 3. Upgrade severity when vision contradicts verbal report
///
/// This mirrors real clinical practice: history + physical examination.
/// Two independent data sources cross-checking each other.
library;

// ============================================================================
// Vision Finding — aggregated across multiple camera frames
// ============================================================================

/// A single clinical finding detected (or not) across multiple camera frames.
class VisionFinding {
  final String key;
  final int detectedCount;
  final int totalFrames;
  final String lastDescription;

  const VisionFinding({
    required this.key,
    required this.detectedCount,
    required this.totalFrames,
    this.lastDescription = '',
  });

  bool get detected => detectedCount > totalFrames / 2;
  double get confidence =>
      totalFrames > 0 ? detectedCount / totalFrames : 0.0;
  String get confidenceLabel =>
      '${detectedCount}/${totalFrames} frames';
}

// ============================================================================
// Vision Aggregator — accumulates findings across frames
// ============================================================================

/// Aggregates vision analysis results from multiple camera frames.
///
/// Each frame produces findings for alertness, chest, dehydration, nutrition.
/// The aggregator counts detections across frames to build confidence.
class VisionAggregator {
  int totalFrames = 0;
  final Map<String, int> _detectionCounts = {};
  final Map<String, String> _lastDescriptions = {};
  final List<String> _allNotes = [];

  /// Add findings from a single analyzed frame.
  void addFrame(Map<String, bool> frameFindings, String notes) {
    totalFrames++;
    for (final entry in frameFindings.entries) {
      _detectionCounts.putIfAbsent(entry.key, () => 0);
      if (entry.value) {
        _detectionCounts[entry.key] = _detectionCounts[entry.key]! + 1;
      }
    }
    if (notes.isNotEmpty) {
      _lastDescriptions['notes'] = notes;
      _allNotes.add(notes);
    }
  }

  /// Get aggregated findings with confidence scores.
  Map<String, VisionFinding> get findings {
    final result = <String, VisionFinding>{};
    for (final key in _detectionCounts.keys) {
      result[key] = VisionFinding(
        key: key,
        detectedCount: _detectionCounts[key] ?? 0,
        totalFrames: totalFrames,
        lastDescription: _lastDescriptions[key] ?? '',
      );
    }
    return result;
  }

  /// All observation notes from analyzed frames.
  List<String> get notes => List.unmodifiable(_allNotes);
}

// ============================================================================
// Reconciliation Warning
// ============================================================================

/// A conflict between questionnaire and vision assessment.
class ReconciliationWarning {
  /// Clinical category: 'alertness', 'breathing', 'dehydration', 'nutrition'.
  final String category;

  /// What the questionnaire reported.
  final String qaValue;

  /// What the camera detected.
  final String visionValue;

  /// How confident the vision detection is (0.0 - 1.0).
  final double confidence;

  /// Human-readable warning message.
  final String message;

  /// What the caregiver should do.
  final String recommendation;

  /// Warning severity: 'high' (danger sign), 'medium', 'low'.
  final String severity;

  const ReconciliationWarning({
    required this.category,
    required this.qaValue,
    required this.visionValue,
    required this.confidence,
    required this.message,
    required this.recommendation,
    required this.severity,
  });
}

// ============================================================================
// Reconciliation Result
// ============================================================================

/// The combined result of cross-referencing Q&A and vision findings.
class ReconciliationResult {
  /// All vision findings with confidence.
  final Map<String, VisionFinding> visionFindings;

  /// Warnings where Q&A and vision disagree.
  final List<ReconciliationWarning> warnings;

  /// Whether the overall severity was upgraded due to vision findings.
  final bool severityUpgraded;

  /// The new severity if upgraded (null if not).
  final String? upgradedSeverity;

  /// Q&A findings merged with vision corrections.
  final Map<String, dynamic> mergedFindings;

  const ReconciliationResult({
    required this.visionFindings,
    required this.warnings,
    required this.severityUpgraded,
    this.upgradedSeverity,
    required this.mergedFindings,
  });

  bool get hasWarnings => warnings.isNotEmpty;
  bool get hasHighSeverityWarnings =>
      warnings.any((w) => w.severity == 'high');
}

// ============================================================================
// Reconciliation Engine
// ============================================================================

/// Cross-references questionnaire and vision findings.
///
/// The questionnaire captures caregiver-reported symptoms (verbal history).
/// The camera captures visual signs (physical examination).
/// This engine finds where they disagree and generates actionable warnings.
class ReconciliationEngine {
  /// Compare Q&A findings with vision findings and generate warnings.
  static ReconciliationResult reconcile({
    required Map<String, dynamic> qaFindings,
    required Map<String, VisionFinding> visionFindings,
    required String qaSeverity,
  }) {
    final warnings = <ReconciliationWarning>[];
    final merged = Map<String, dynamic>.from(qaFindings);

    // --- Alertness: lethargic ---
    _checkConflict(
      qaFindings: qaFindings,
      visionFindings: visionFindings,
      qaKey: 'lethargic',
      visionKey: 'lethargic',
      category: 'alertness',
      qaFalseLabel: 'Child reported as alert',
      visionTrueLabel: 'Camera detected lethargy',
      message:
          'The camera suggests the child may be lethargic, but the '
          'questionnaire indicated alertness.',
      recommendation:
          'Check if the child responds when you speak to them or '
          'gently shake their shoulder. Lethargy is a danger sign — '
          'if the child is truly lethargic, seek care immediately.',
      severity: 'high',
      warnings: warnings,
      merged: merged,
    );

    // --- Breathing: chest indrawing ---
    _checkConflict(
      qaFindings: qaFindings,
      visionFindings: visionFindings,
      qaKey: 'has_indrawing',
      visionKey: 'chest_indrawing',
      category: 'breathing',
      qaFalseLabel: 'No chest indrawing reported',
      visionTrueLabel: 'Camera detected chest indrawing',
      message:
          'The camera detected possible chest indrawing, but the '
          'questionnaire indicated no indrawing.',
      recommendation:
          'Watch the lower chest wall when the child breathes in. '
          'If it pulls inward, this is chest indrawing — a sign of '
          'severe pneumonia. Seek care immediately.',
      severity: 'high',
      warnings: warnings,
      merged: merged,
    );

    // --- Dehydration: sunken eyes ---
    _checkConflict(
      qaFindings: qaFindings,
      visionFindings: visionFindings,
      qaKey: 'sunken_eyes',
      visionKey: 'dehydration',
      category: 'dehydration',
      qaFalseLabel: 'No dehydration signs reported',
      visionTrueLabel: 'Camera detected dehydration signs',
      message:
          'The camera detected possible dehydration signs (sunken eyes, '
          'dry skin), but the questionnaire indicated no dehydration.',
      recommendation:
          'Check if the child\'s eyes appear sunken. Pinch the skin on '
          'the abdomen — if it goes back slowly, the child may be '
          'dehydrated. Give ORS solution and seek care.',
      severity: 'medium',
      warnings: warnings,
      merged: merged,
    );

    // --- Nutrition: visible wasting ---
    _checkConflict(
      qaFindings: qaFindings,
      visionFindings: visionFindings,
      qaKey: 'visible_wasting',
      visionKey: 'wasting',
      category: 'nutrition',
      qaFalseLabel: 'No visible wasting reported',
      visionTrueLabel: 'Camera detected visible wasting',
      message:
          'The camera detected possible visible wasting (very thin, '
          'ribs visible), but the questionnaire indicated no wasting.',
      recommendation:
          'Look at the child\'s ribs and shoulders. If bones are '
          'clearly visible, this is visible wasting — a sign of severe '
          'malnutrition. The child needs nutritional support.',
      severity: 'medium',
      warnings: warnings,
      merged: merged,
    );

    // --- Nutrition: edema ---
    _checkConflict(
      qaFindings: qaFindings,
      visionFindings: visionFindings,
      qaKey: 'edema',
      visionKey: 'edema',
      category: 'nutrition',
      qaFalseLabel: 'No edema reported',
      visionTrueLabel: 'Camera detected edema',
      message:
          'The camera detected possible swelling in the feet (edema), '
          'but the questionnaire indicated no edema.',
      recommendation:
          'Press both feet gently for 3 seconds. If a dent remains, '
          'this is edema — a sign of severe malnutrition. Seek care.',
      severity: 'medium',
      warnings: warnings,
      merged: merged,
    );

    // --- Check for vision confirming concerns ---
    // When BOTH Q&A and vision agree on a problem, note it as confirmed.
    _checkConfirmation(
      qaFindings: qaFindings,
      visionFindings: visionFindings,
      qaKey: 'lethargic',
      visionKey: 'lethargic',
      category: 'alertness',
      message: 'Both questionnaire and camera confirm lethargy.',
      recommendation: 'This is a confirmed danger sign. Seek care immediately.',
      severity: 'high',
      warnings: warnings,
    );

    // --- Severity upgrade ---
    var upgraded = false;
    String? newSeverity;
    if (qaSeverity != 'red') {
      // Check if any high-severity vision finding should upgrade
      final hasVisionDangerSign = warnings.any(
        (w) => w.severity == 'high' && w.visionValue.isNotEmpty,
      );
      if (hasVisionDangerSign) {
        upgraded = true;
        newSeverity = 'red';
      } else if (qaSeverity == 'green' &&
          warnings.any((w) => w.severity == 'medium')) {
        upgraded = true;
        newSeverity = 'yellow';
      }
    }

    return ReconciliationResult(
      visionFindings: visionFindings,
      warnings: warnings,
      severityUpgraded: upgraded,
      upgradedSeverity: newSeverity,
      mergedFindings: merged,
    );
  }

  /// Check for a conflict where Q&A says false but vision says true.
  static void _checkConflict({
    required Map<String, dynamic> qaFindings,
    required Map<String, VisionFinding> visionFindings,
    required String qaKey,
    required String visionKey,
    required String category,
    required String qaFalseLabel,
    required String visionTrueLabel,
    required String message,
    required String recommendation,
    required String severity,
    required List<ReconciliationWarning> warnings,
    required Map<String, dynamic> merged,
  }) {
    final vf = visionFindings[visionKey];
    if (vf == null) return;

    final qaValue = qaFindings[qaKey];
    final qaIsFalse = qaValue == null || qaValue == false;

    if (qaIsFalse && vf.detected) {
      warnings.add(ReconciliationWarning(
        category: category,
        qaValue: qaFalseLabel,
        visionValue: visionTrueLabel,
        confidence: vf.confidence,
        message: message,
        recommendation: recommendation,
        severity: severity,
      ));
      // Update merged findings — vision overrides Q&A for this finding
      merged['${qaKey}_vision_override'] = true;
      merged['${qaKey}_vision_confidence'] = vf.confidence;
    }
  }

  /// Check where both Q&A and vision agree on a positive finding.
  static void _checkConfirmation({
    required Map<String, dynamic> qaFindings,
    required Map<String, VisionFinding> visionFindings,
    required String qaKey,
    required String visionKey,
    required String category,
    required String message,
    required String recommendation,
    required String severity,
    required List<ReconciliationWarning> warnings,
  }) {
    final vf = visionFindings[visionKey];
    if (vf == null) return;

    final qaIsTrue = qaFindings[qaKey] == true;
    if (qaIsTrue && vf.detected) {
      warnings.add(ReconciliationWarning(
        category: category,
        qaValue: 'Reported by caregiver',
        visionValue: 'Confirmed by camera',
        confidence: vf.confidence,
        message: message,
        recommendation: recommendation,
        severity: severity,
      ));
    }
  }
}
