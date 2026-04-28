/// Agentic Orchestrator — pure helpers for intelligent Q&A.
///
/// All functions here are pure (no I/O, no Flutter, no model). They build
/// prompts and parse responses. The model invocation lives in `home_screen`
/// — keeping these pure makes them easy to unit-test and easy to revert if
/// a phase misbehaves.
///
/// Phase 1: structured multi-value extraction
/// Phase 2: agentic next-question selection (TODO)
/// Phase 3: context-aware question wording (TODO)
/// Phase 4: rich final report builders (TODO)
library;

import 'dart:convert';

import 'imci_questionnaire.dart';

// ============================================================================
// Feature flag
// ============================================================================

/// Single switch for the entire agentic-orchestration upgrade. Off → app
/// behaves exactly as before this branch. On → Phase 1+ helpers activate
/// with their own per-call fallbacks. Lets us A/B revert during demos
/// without touching code.
const bool kAgenticOrchestration = true;

// ============================================================================
// Phase 1 — Structured Multi-Value Extraction
// ============================================================================

/// JSON-schema type tag for a question.
String? _typeHint(AnswerType t) => switch (t) {
      AnswerType.yesNo => 'true/false',
      AnswerType.number => 'number',
      AnswerType.age => 'number',
      AnswerType.photo => null,
    };

/// Build a tight structured-extraction prompt for the model.
///
/// Always includes the [currentQuestion]'s key in the schema so the
/// caregiver's answer can override an earlier vision finding for the
/// same field. Other keys in the step are included only if not already
/// answered.
///
/// Token budget: ≤ ~90 tokens of prompt for a 4-question step. Response
/// is a small JSON object (~30 tokens). Fits inside the model's
/// 200-token context with room for the system instruction.
String buildStructuredExtractPrompt({
  required ImciQuestion currentQuestion,
  required List<ImciQuestion> stepQuestions,
  required Map<String, dynamic> knownFindings,
  required Set<String> answeredIds,
  required String userText,
}) {
  final lines = <String>[];

  // Always include the current question's key — the caregiver is answering
  // it now, even if vision pre-populated something for the same field.
  final currentType = _typeHint(currentQuestion.type);
  if (currentType != null) {
    lines.add('${currentQuestion.id}: $currentType');
  }

  for (final q in stepQuestions) {
    if (q.id == currentQuestion.id) continue;
    final type = _typeHint(q.type);
    if (type == null) continue;
    if (answeredIds.contains(q.id)) continue;
    final v = knownFindings[q.id];
    final alreadyTrue = v == true || (v is num && v > 0);
    if (alreadyTrue) continue;
    lines.add('${q.id}: $type');
  }

  if (lines.isEmpty) return '';

  final schema = lines.join(', ');
  return 'Caregiver was just asked: "${currentQuestion.question}" '
      'Caregiver said: "$userText". '
      'Extract ONLY findings the caregiver explicitly stated. '
      'If they only answered the question above, include just that key. '
      'Do NOT infer other findings from a single yes/no. '
      'Possible keys: $schema. '
      'Reply ONLY with a JSON object. '
      'Example: {"${currentQuestion.id}": ${_exampleValueForType(currentQuestion.type)}}';
}

String _exampleValueForType(AnswerType t) => switch (t) {
      AnswerType.yesNo => 'true',
      AnswerType.number => '2',
      AnswerType.age => '12',
      AnswerType.photo => '""',
    };

/// Allowed-key whitelist for a step. Used to drop hallucinated fields.
Set<String> allowedKeysForStep(List<ImciQuestion> stepQuestions) =>
    stepQuestions.map((q) => q.id).toSet();

/// Parse the model's response into a sanitized findings map.
///
/// Tolerant: scans for the first `{` and last `}` to extract the JSON
/// object, even if the model added prose around it. Returns null on any
/// parse failure so the caller can fall back to single-value extraction.
///
/// Type-coerces values per question type and drops any key not in
/// [allowedKeys] (defends against hallucinated fields).
Map<String, dynamic>? parseStructuredResponse({
  required String raw,
  required List<ImciQuestion> stepQuestions,
}) {
  final start = raw.indexOf('{');
  final end = raw.lastIndexOf('}');
  if (start < 0 || end <= start) return null;

  final jsonStr = raw.substring(start, end + 1);
  Map<String, dynamic> decoded;
  try {
    final parsed = jsonDecode(jsonStr);
    if (parsed is! Map<String, dynamic>) return null;
    decoded = parsed;
  } catch (_) {
    return null;
  }

  final byId = {for (final q in stepQuestions) q.id: q};
  final out = <String, dynamic>{};

  for (final entry in decoded.entries) {
    final q = byId[entry.key];
    if (q == null) continue; // unknown key — drop

    final coerced = _coerce(entry.value, q.type);
    if (coerced == null) continue;
    out[entry.key] = coerced;
  }

  return out.isEmpty ? null : out;
}

/// Coerce a JSON value to the type expected for an IMCI question.
/// Returns null if the value cannot be safely interpreted (caller drops it).
dynamic _coerce(dynamic v, AnswerType type) {
  switch (type) {
    case AnswerType.yesNo:
      if (v is bool) return v;
      if (v is String) {
        final s = v.trim().toLowerCase();
        if (s == 'true' || s == 'yes') return true;
        if (s == 'false' || s == 'no') return false;
      }
      return null;
    case AnswerType.number:
    case AnswerType.age:
      if (v is int) return v >= 0 ? v : null;
      if (v is double) return v >= 0 ? v.toInt() : null;
      if (v is String) {
        final parsed = int.tryParse(v.trim());
        if (parsed != null && parsed >= 0) return parsed;
      }
      return null;
    case AnswerType.photo:
      return null;
  }
}
