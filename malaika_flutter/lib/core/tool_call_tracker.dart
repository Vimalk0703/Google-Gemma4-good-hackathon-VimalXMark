/// Agentic tool call instrumentation for Malaika IMCI assessment.
///
/// Wraps each deterministic operation (text extraction, vision analysis,
/// WHO classification, LLM generation) as a measured "tool call" with
/// skill metadata from [SkillRegistry]. Produces [BenchmarkSummary]
/// with real timing numbers for the hackathon benchmark card.
///
/// Zero GPU impact — pure Dart bookkeeping.
library;

import 'skills.dart';

// ============================================================================
// Tool Call Event
// ============================================================================

/// A single recorded tool call with timing and result metadata.
class ToolCallEvent {
  /// Skill name from SkillRegistry (e.g. "parse_caregiver_response").
  final String skillName;

  /// IMCI step this call belongs to.
  final String imciStep;

  /// Input modality: "text", "image", "findings".
  final String inputType;

  /// Wall-clock start time.
  final DateTime startTime;

  /// Wall-clock end time.
  DateTime? endTime;

  /// Duration in milliseconds.
  int get durationMs =>
      endTime != null ? endTime!.difference(startTime).inMilliseconds : 0;

  /// Whether the call succeeded.
  bool success;

  /// Approximate input token count (words * 1.3).
  int inputTokenEstimate;

  /// Approximate output token count.
  int outputTokenEstimate;

  /// Extracted findings from this call.
  Map<String, dynamic> findings;

  /// How the output was parsed.
  String parseMethod;

  /// Confidence score (1.0 for deterministic, variable for LLM/vision).
  double confidence;

  ToolCallEvent({
    required this.skillName,
    required this.imciStep,
    required this.inputType,
    required this.startTime,
    this.endTime,
    this.success = false,
    this.inputTokenEstimate = 0,
    this.outputTokenEstimate = 0,
    Map<String, dynamic>? findings,
    this.parseMethod = '',
    this.confidence = 0.0,
  }) : findings = findings ?? {};

  Map<String, dynamic> toMap() => {
        'skill': skillName,
        'step': imciStep,
        'input': inputType,
        'ms': durationMs,
        'success': success,
        'method': parseMethod,
        'confidence': confidence,
        'tokensIn': inputTokenEstimate,
        'tokensOut': outputTokenEstimate,
        'findings': findings,
      };
}

// ============================================================================
// Benchmark Summary
// ============================================================================

/// Aggregate benchmark stats across all tool calls in an assessment.
class BenchmarkSummary {
  final int totalToolCalls;
  final int totalDurationMs;
  final double avgLatencyMs;
  final double medianLatencyMs;
  final int successCount;
  final double successRate;
  final int totalInputTokens;
  final int totalOutputTokens;
  final int llmCallCount;
  final int llmTotalMs;
  final int visionCallCount;
  final int visionTotalMs;
  final int deterministicCallCount;
  final int deterministicTotalMs;
  final Map<String, SkillBreakdown> bySkill;
  final Map<String, int> byStep;

  const BenchmarkSummary({
    required this.totalToolCalls,
    required this.totalDurationMs,
    required this.avgLatencyMs,
    required this.medianLatencyMs,
    required this.successCount,
    required this.successRate,
    required this.totalInputTokens,
    required this.totalOutputTokens,
    required this.llmCallCount,
    required this.llmTotalMs,
    required this.visionCallCount,
    required this.visionTotalMs,
    required this.deterministicCallCount,
    required this.deterministicTotalMs,
    required this.bySkill,
    required this.byStep,
  });

  Map<String, dynamic> toMap() => {
        'totalToolCalls': totalToolCalls,
        'totalDurationMs': totalDurationMs,
        'avgLatencyMs': avgLatencyMs.round(),
        'medianLatencyMs': medianLatencyMs.round(),
        'successRate': '${(successRate * 100).round()}%',
        'totalInputTokens': totalInputTokens,
        'totalOutputTokens': totalOutputTokens,
        'llmCalls': llmCallCount,
        'llmTotalMs': llmTotalMs,
        'visionCalls': visionCallCount,
        'visionTotalMs': visionTotalMs,
        'deterministicCalls': deterministicCallCount,
        'deterministicTotalMs': deterministicTotalMs,
        'bySkill': bySkill.map((k, v) => MapEntry(k, v.toMap())),
        'byStep': byStep,
      };
}

class SkillBreakdown {
  final int count;
  final int totalMs;
  final double avgMs;

  const SkillBreakdown({
    required this.count,
    required this.totalMs,
    required this.avgMs,
  });

  Map<String, dynamic> toMap() => {
        'count': count,
        'totalMs': totalMs,
        'avgMs': avgMs.round(),
      };
}

// ============================================================================
// Tool Call Tracker
// ============================================================================

/// Tracks tool call events throughout an IMCI assessment.
///
/// Usage:
/// ```dart
/// tracker.startCall('parse_caregiver_response', step: 'danger_signs');
/// // ... do the work ...
/// tracker.endCall(findings: {...}, success: true, parseMethod: 'keyword_match');
/// ```
class ToolCallTracker {
  final List<ToolCallEvent> _events = [];
  final BeliefState belief = BeliefState();

  ToolCallEvent? _current;

  /// All recorded events.
  List<ToolCallEvent> get events => List.unmodifiable(_events);

  /// Start timing a tool call.
  void startCall(String skillName, {String? step, String? inputType}) {
    // Look up skill metadata from registry if available
    String resolvedStep = step ?? 'unknown';
    String resolvedInput = inputType ?? 'text';

    try {
      final skill = SkillRegistry.get(skillName);
      resolvedStep = step ?? skill.imciStep;
      resolvedInput = inputType ?? skill.inputType;
    } catch (_) {
      // Skill not in registry — use provided values
    }

    _current = ToolCallEvent(
      skillName: skillName,
      imciStep: resolvedStep,
      inputType: resolvedInput,
      startTime: DateTime.now(),
    );
  }

  /// End timing and record the tool call.
  void endCall({
    Map<String, dynamic>? findings,
    bool success = true,
    String parseMethod = '',
    double confidence = 1.0,
    int? inputTokens,
    int? outputTokens,
  }) {
    if (_current == null) return;

    _current!
      ..endTime = DateTime.now()
      ..success = success
      ..findings = findings ?? {}
      ..parseMethod = parseMethod
      ..confidence = confidence
      ..inputTokenEstimate = inputTokens ?? 0
      ..outputTokenEstimate = outputTokens ?? 0;

    // Update belief state
    if (success && findings != null) {
      for (final entry in findings.entries) {
        belief.confirmFinding(entry.key, entry.value);
      }
    }

    _events.add(_current!);
    _current = null;
  }

  /// Get the last completed event (for showing in UI).
  ToolCallEvent? get lastEvent => _events.isNotEmpty ? _events.last : null;

  /// Compute aggregate benchmark summary.
  BenchmarkSummary summarize() {
    if (_events.isEmpty) {
      return const BenchmarkSummary(
        totalToolCalls: 0,
        totalDurationMs: 0,
        avgLatencyMs: 0,
        medianLatencyMs: 0,
        successCount: 0,
        successRate: 1.0,
        totalInputTokens: 0,
        totalOutputTokens: 0,
        llmCallCount: 0,
        llmTotalMs: 0,
        visionCallCount: 0,
        visionTotalMs: 0,
        deterministicCallCount: 0,
        deterministicTotalMs: 0,
        bySkill: {},
        byStep: {},
      );
    }

    final durations = _events.map((e) => e.durationMs).toList()..sort();
    final totalMs = durations.fold(0, (a, b) => a + b);
    final successCount = _events.where((e) => e.success).length;
    final totalIn = _events.fold(0, (a, e) => a + e.inputTokenEstimate);
    final totalOut = _events.fold(0, (a, e) => a + e.outputTokenEstimate);

    // Median
    final mid = durations.length ~/ 2;
    final median = durations.length % 2 == 0
        ? (durations[mid - 1] + durations[mid]) / 2.0
        : durations[mid].toDouble();

    // LLM vs vision vs deterministic
    final llmEvents =
        _events.where((e) => e.parseMethod == 'gemma4_generation').toList();
    final visionEvents =
        _events.where((e) => e.parseMethod == 'vision_analysis').toList();
    final detEvents = _events
        .where((e) =>
            e.parseMethod != 'gemma4_generation' &&
            e.parseMethod != 'vision_analysis')
        .toList();

    // By skill
    final skillMap = <String, List<ToolCallEvent>>{};
    for (final e in _events) {
      skillMap.putIfAbsent(e.skillName, () => []).add(e);
    }
    final bySkill = skillMap.map((name, events) {
      final total = events.fold(0, (a, e) => a + e.durationMs);
      return MapEntry(
        name,
        SkillBreakdown(
          count: events.length,
          totalMs: total,
          avgMs: total / events.length,
        ),
      );
    });

    // By step
    final stepMap = <String, int>{};
    for (final e in _events) {
      stepMap[e.imciStep] = (stepMap[e.imciStep] ?? 0) + 1;
    }

    return BenchmarkSummary(
      totalToolCalls: _events.length,
      totalDurationMs: totalMs,
      avgLatencyMs: totalMs / _events.length,
      medianLatencyMs: median,
      successCount: successCount,
      successRate: successCount / _events.length,
      totalInputTokens: totalIn,
      totalOutputTokens: totalOut,
      llmCallCount: llmEvents.length,
      llmTotalMs: llmEvents.fold(0, (a, e) => a + e.durationMs),
      visionCallCount: visionEvents.length,
      visionTotalMs: visionEvents.fold(0, (a, e) => a + e.durationMs),
      deterministicCallCount: detEvents.length,
      deterministicTotalMs: detEvents.fold(0, (a, e) => a + e.durationMs),
      bySkill: bySkill,
      byStep: stepMap,
    );
  }
}
