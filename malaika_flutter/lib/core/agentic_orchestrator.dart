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
import 'skills.dart';

// ============================================================================
// Feature flag
// ============================================================================

/// Single switch for the entire agentic-orchestration upgrade. Off → app
/// behaves exactly as before this branch. On → Phase 1+ helpers activate
/// with their own per-call fallbacks. Lets us A/B revert during demos
/// without touching code.
const bool kAgenticOrchestration = true;

// ============================================================================
// P2.5/P2.6 — Belief + Skill context for prompts
// ============================================================================

/// Render the belief snapshot as a one-line preamble for prompts.
/// Examples:
///   "" (empty when nothing is known)
///   "Known: lethargic, sunken_eyes, age_months=12, fever_days=2."
///
/// Token budget: ≤ ~30 tokens for typical end-of-assessment belief sets.
/// Skips false booleans and zero numerics — only positive findings carry
/// clinical signal worth giving the model.
String formatBeliefForPrompt(Map<String, dynamic> belief) {
  if (belief.isEmpty) return '';
  final items = <String>[];
  belief.forEach((k, v) {
    if (v == true) items.add(k);
    else if (v is num && v > 0) items.add('$k=$v');
  });
  if (items.isEmpty) return '';
  return 'Known: ${items.join(', ')}.';
}

/// Render the active skill's contract as a one-line prompt prefix so the
/// model sees the registered skill, not just hand-written instructions.
/// Returns empty string if the skill name isn't in the registry.
///
/// Token budget: ~15-25 tokens depending on the skill description.
String formatSkillContext(String skillName) {
  try {
    final skill = SkillRegistry.get(skillName);
    return 'Skill: ${skill.name} — ${skill.description}';
  } catch (_) {
    return '';
  }
}

/// Compose belief + skill prefix as a single block. Either or both may be
/// empty; we return only the non-empty parts joined by a newline.
String composePromptPrefix({String? skillName, Map<String, dynamic>? belief}) {
  final parts = <String>[];
  if (skillName != null) {
    final s = formatSkillContext(skillName);
    if (s.isNotEmpty) parts.add(s);
  }
  if (belief != null) {
    final b = formatBeliefForPrompt(belief);
    if (b.isNotEmpty) parts.add(b);
  }
  return parts.isEmpty ? '' : '${parts.join('\n')}\n';
}

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
  final prefix = composePromptPrefix(
    skillName: 'extract_structured_findings',
    belief: knownFindings,
  );

  return '${prefix}Caregiver was just asked: "${currentQuestion.question}" '
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

// ============================================================================
// Phase 2 — Agentic Next-Question Selection
// ============================================================================

/// Build a prompt asking Gemma to pick the most clinically important
/// question to ask NEXT, given what we already know.
///
/// Constraints:
///   - The picker only sees questions remaining within the CURRENT IMCI step
///     (we never reorder across steps — danger → breathing → diarrhea → fever
///     → nutrition is the WHO IMCI flow and stays preserved).
///   - The response is a single question_id; everything else is ignored.
///
/// Token budget: ≤ ~120 tokens of prompt for a typical 4-question step,
/// ~5 tokens of response. Comfortable inside the model's 200-token window.
String pickNextQuestionPrompt({
  required Map<String, dynamic> knownFindings,
  required List<ImciQuestion> remaining,
}) {
  final ids = remaining.map((q) => q.id).join(', ');
  final prefix = composePromptPrefix(
    skillName: 'select_next_question',
    belief: knownFindings,
  );

  return '${prefix}Choose the most clinically important next question. '
      'Reply with EXACTLY one of these ids: $ids. '
      'Output ONLY the id text — no numbers, no quotes, no other words.';
}

/// Parse a model response into a question id from the allowed whitelist.
/// Tolerates surrounding prose/quotes/newlines — finds the first id that
/// appears in the response. Returns null if no allowed id is found.
String? parseNextQuestionId(String raw, Set<String> validIds) {
  final cleaned = raw.toLowerCase();
  // Sort by length desc so longer ids match before their substrings (e.g.
  // "fever_days" before "fever").
  final sorted = validIds.toList()
    ..sort((a, b) => b.length.compareTo(a.length));
  for (final id in sorted) {
    if (cleaned.contains(id.toLowerCase())) return id;
  }
  return null;
}

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
