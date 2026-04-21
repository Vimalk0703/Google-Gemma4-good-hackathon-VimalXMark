/// Agentic Assessor — vision-driven question selection.
///
/// This is WHERE Gemma 4's agentic capability shines.
/// Instead of walking through all 20 IMCI questions, it analyzes
/// what the vision model already detected and selects ONLY the
/// questions needed to complete the clinical picture.
///
/// Fallback: if photo is skipped, returns the full IMCI questionnaire.
library;

import 'imci_questionnaire.dart';

// ============================================================================
// Vision Finding Keys — what Gemma 4 vision can detect from a photo
// ============================================================================

/// Possible findings from a comprehensive vision analysis.
/// These map to IMCI assessment domains.
class VisionKeys {
  // Alertness / danger signs
  static const lethargic = 'vision_lethargic';
  static const unconscious = 'vision_unconscious';

  // Dehydration signs
  static const sunkenEyes = 'vision_sunken_eyes';
  static const dryLips = 'vision_dry_lips';
  static const dehydrated = 'vision_dehydrated';

  // Nutrition
  static const wasting = 'vision_wasting';
  static const edema = 'vision_edema';
  static const pallor = 'vision_pallor';

  // Skin / rash
  static const rash = 'vision_rash';
  static const measlesRash = 'vision_measles_rash';

  // Breathing (limited from photo)
  static const nasalFlaring = 'vision_nasal_flaring';
  static const respiratoryDistress = 'vision_respiratory_distress';
}

// ============================================================================
// Comprehensive Vision Prompt — single photo, multiple assessments
// ============================================================================

/// System instruction for the vision session — empty to save tokens.
/// All instructions go in the user prompt instead.
const String visionSystemPrompt = 'Check this child for health signs.';

/// Ultra-short vision prompt — must fit in ~90 tokens.
///
/// Token budget (maxTokens=200 — proven stable on A53 Mali G68):
///   Image: ~70 tokens (256px, smallest token budget)
///   System: ~10 tokens
///   This prompt: ~90 tokens
///   Total input: ~170 — under 200 limit
///   Output: generated after input, not counted against limit
///
/// Each line has a brief visual cue so the 2B model knows what to look for.
const String comprehensiveVisionPrompt =
    'Answer YES or NO for each:\n'
    'LETHARGIC (eyes closed, limp): YES/NO\n'
    'SUNKEN_EYES (deep in sockets): YES/NO\n'
    'WASTING (very thin, ribs showing): YES/NO\n'
    'EDEMA (swollen feet): YES/NO\n'
    'PALLOR (pale skin/lips): YES/NO\n'
    'RASH (spots or rash): YES/NO';

// ============================================================================
// Parse Vision Response
// ============================================================================

/// Parse the structured vision response into a findings map.
/// Tolerant of formatting variations — checks for YES/NO per line.
Map<String, bool> parseVisionResponse(String response) {
  final findings = <String, bool>{};
  final lines = response.toUpperCase().split('\n');

  for (final line in lines) {
    final trimmed = line.trim();
    if (trimmed.isEmpty) continue;

    // Check for each finding keyword — tolerant of formatting variations
    if (trimmed.contains('LETHARGIC')) {
      findings[VisionKeys.lethargic] = trimmed.contains('YES');
    } else if (trimmed.contains('SUNKEN') && trimmed.contains('EYE')) {
      findings[VisionKeys.sunkenEyes] = trimmed.contains('YES');
    } else if (trimmed.contains('WASTING') || (trimmed.contains('THIN') && !trimmed.contains('SUMMARY'))) {
      findings[VisionKeys.wasting] = trimmed.contains('YES');
    } else if (trimmed.contains('EDEMA') || trimmed.contains('SWELLING')) {
      findings[VisionKeys.edema] = trimmed.contains('YES');
    } else if (trimmed.contains('PALLOR') || trimmed.contains('PALE')) {
      findings[VisionKeys.pallor] = trimmed.contains('YES');
    } else if (trimmed.contains('RASH') && !trimmed.contains('SUMMARY')) {
      findings[VisionKeys.rash] = trimmed.contains('YES');
    }
    // SUMMARY line is not a finding — it's for UI display
  }

  // Mark dehydrated if sunken eyes detected
  findings[VisionKeys.dehydrated] =
      findings[VisionKeys.sunkenEyes] ?? false;

  // Rash could indicate measles — follow-up Q will confirm
  findings[VisionKeys.measlesRash] =
      findings[VisionKeys.rash] ?? false;

  return findings;
}

/// Extract the SUMMARY sentence from the vision response (for UI display).
String extractVisionSummary(String response) {
  final lines = response.split('\n');
  for (final line in lines) {
    final trimmed = line.trim();
    if (trimmed.toUpperCase().startsWith('SUMMARY')) {
      // Remove "SUMMARY:" prefix
      final idx = trimmed.indexOf(':');
      return idx >= 0 ? trimmed.substring(idx + 1).trim() : trimmed;
    }
  }
  // If no SUMMARY line, return the last non-empty line
  for (var i = lines.length - 1; i >= 0; i--) {
    final trimmed = lines[i].trim();
    if (trimmed.isNotEmpty && !trimmed.contains(':')) return trimmed;
  }
  return '';
}

// ============================================================================
// Agentic Question Selection
// ============================================================================

/// Select targeted IMCI questions based on what Gemma 4 SEES in the photo.
///
/// This is the core agentic logic: the model looks first, then asks only
/// what it can't determine from the photo.
///
/// Returns a filtered list of ImciQuestion objects in IMCI protocol order.
/// If no vision findings (photo skipped), returns the full question set.
List<ImciQuestion> selectTargetedQuestions({
  required Map<String, bool> visionFindings,
  required int ageMonths,
}) {
  // If no vision findings at all, fall back to full questionnaire
  if (visionFindings.isEmpty) {
    return imciQuestions.where((q) => q.step != 'greeting').toList();
  }

  final selected = <ImciQuestion>[];

  // ── ALWAYS ASK: Core danger signs (can't fully assess from photo) ──
  // These require caregiver's verbal report
  _addQuestion(selected, 'unable_to_drink');
  _addQuestion(selected, 'vomits_everything');
  _addQuestion(selected, 'has_convulsions');

  // Skip lethargic Q if vision already determined it
  if (visionFindings[VisionKeys.lethargic] != true &&
      visionFindings[VisionKeys.unconscious] != true) {
    _addQuestion(selected, 'lethargic');
  }

  // ── BREATHING: Always ask about cough (can't hear from photo) ──
  _addQuestion(selected, 'has_cough');
  // Indrawing: if vision saw nasal flaring/distress, ask about indrawing too
  if (visionFindings[VisionKeys.nasalFlaring] == true ||
      visionFindings[VisionKeys.respiratoryDistress] == true) {
    _addQuestion(selected, 'has_indrawing');
    _addQuestion(selected, 'has_wheeze');
  }

  // ── DIARRHEA: Always ask (can't determine from photo) ──
  _addQuestion(selected, 'has_diarrhea');
  // If vision detected dehydration signs, definitely ask diarrhea follow-ups
  if (visionFindings[VisionKeys.dehydrated] == true) {
    _addQuestion(selected, 'diarrhea_days');
    _addQuestion(selected, 'blood_in_stool');
    _addQuestion(selected, 'sunken_eyes'); // Confirm vision finding verbally
  }

  // ── FEVER: Always ask (can't measure from photo) ──
  _addQuestion(selected, 'has_fever');
  // If vision saw rash, ask fever follow-ups (measles pathway)
  if (visionFindings[VisionKeys.rash] == true) {
    _addQuestion(selected, 'fever_days');
    _addQuestion(selected, 'stiff_neck');
    _addQuestion(selected, 'malaria_risk');
  }

  // ── NUTRITION: Skip if vision clearly determined ──
  // Only ask about wasting/edema if vision was unclear
  if (visionFindings[VisionKeys.wasting] == null) {
    _addQuestion(selected, 'visible_wasting');
  }
  if (visionFindings[VisionKeys.edema] == null) {
    _addQuestion(selected, 'edema');
  }

  return selected;
}

/// Helper: add a question by ID if it exists in the master list.
void _addQuestion(List<ImciQuestion> selected, String questionId) {
  final q = imciQuestions.where((q) => q.id == questionId).firstOrNull;
  if (q != null && !selected.any((s) => s.id == questionId)) {
    selected.add(q);
  }
}

/// Pre-populate IMCI findings from vision analysis.
///
/// Maps vision findings to the questionnaire's finding keys so
/// classification can use them.
Map<String, dynamic> visionToImciFindings(Map<String, bool> visionFindings) {
  final findings = <String, dynamic>{};

  // Map vision keys to IMCI finding keys
  if (visionFindings[VisionKeys.lethargic] == true) {
    findings['lethargic'] = true;
  }
  if (visionFindings[VisionKeys.unconscious] == true) {
    findings['lethargic'] = true; // IMCI treats unconscious as lethargy+
  }
  if (visionFindings[VisionKeys.sunkenEyes] == true) {
    findings['sunken_eyes'] = true;
  }
  if (visionFindings[VisionKeys.wasting] == true) {
    findings['visible_wasting'] = true;
  }
  if (visionFindings[VisionKeys.edema] == true) {
    findings['edema'] = true;
  }

  return findings;
}

/// Count how many questions were skipped due to vision findings.
int questionsSaved({
  required Map<String, bool> visionFindings,
  required int ageMonths,
}) {
  final fullCount = imciQuestions.where((q) => q.step != 'greeting').length;
  final targetedCount = selectTargetedQuestions(
    visionFindings: visionFindings,
    ageMonths: ageMonths,
  ).length;
  return fullCount - targetedCount;
}
