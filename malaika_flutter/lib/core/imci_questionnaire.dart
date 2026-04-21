/// IMCI Questionnaire — structured Q&A collection for WHO IMCI assessment.
///
/// This module defines the ordered list of clinical questions following the
/// WHO IMCI protocol. Each question maps directly to a clinical finding.
/// No regex, no keyword matching — the question defines the context,
/// so "yes"/"no" maps unambiguously to the finding.
///
/// Architecture:
///   Phase 1: Ask questions in order, collect answers
///   Phase 2: Classify per step using imci_protocol.dart (deterministic)
///   Phase 3: LLM narrates the final report from all Q&A + classifications
library;

import 'imci_protocol.dart';
import 'imci_types.dart';

// ============================================================================
// Question Types
// ============================================================================

enum AnswerType {
  /// Yes/No boolean question. "yes" = yesValue, "no" = noValue.
  yesNo,

  /// Numeric answer (e.g., "how many days?").
  number,

  /// Free text (e.g., age — needs special parsing).
  age,

  /// Photo-based assessment. User takes a photo, Gemma 4 vision analyzes it
  /// with a targeted clinical prompt. The LLM's analysis becomes the finding.
  photo,
}

// ============================================================================
// Vision Analysis Prompts — targeted clinical directives per IMCI step
// ============================================================================

/// Clinical vision prompt for Gemma 4 image analysis.
/// Each prompt tells the model EXACTLY what to look for in the photo.
class VisionPrompt {
  /// The IMCI step this analysis belongs to.
  final String step;

  /// What to say when asking the user for a photo.
  final String askText;

  /// The clinical directive sent to Gemma 4 with the image.
  /// Must be specific: "Look for X, Y, Z" not "describe this child".
  final String analysisPrompt;

  /// Finding keys that this analysis can update.
  final List<String> findingKeys;

  const VisionPrompt({
    required this.step,
    required this.askText,
    required this.analysisPrompt,
    required this.findingKeys,
  });
}

/// Targeted vision prompts per IMCI step.
const Map<String, VisionPrompt> visionPrompts = {
  'danger_signs': VisionPrompt(
    step: 'danger_signs',
    askText:
        'Can you take a photo of your child? I want to check how alert they are.',
    analysisPrompt:
        'You are a child health assistant. Look at this child carefully and assess alertness.\n'
        'CHECK SPECIFICALLY:\n'
        '1. EYES: Are they open and tracking, or closed/unfocused?\n'
        '2. POSTURE: Is the child sitting/moving normally, or floppy/limp?\n'
        '3. EXPRESSION: Does the child appear aware of surroundings, or blank/unresponsive?\n'
        '4. RESPONSIVENESS: Does the child look like they would respond if spoken to?\n\n'
        'A child is LETHARGIC if abnormally sleepy, difficult to wake, or not looking at caregiver.\n'
        'A child is UNCONSCIOUS if they cannot be woken at all.\n\n'
        'Reply with ONLY: ALERT, LETHARGIC, or UNCONSCIOUS — then one sentence describing what you see.',
    findingKeys: ['lethargic'],
  ),
  'breathing': VisionPrompt(
    step: 'breathing',
    askText:
        'Can you take a photo of your child\'s chest? I want to check their breathing.',
    analysisPrompt:
        'You are a child health assistant. Look at this child\'s chest area.\n'
        'CHECK SPECIFICALLY:\n'
        '1. CHEST INDRAWING: Does the lower chest wall pull INWARD when the child breathes in?\n'
        '   (Normal: chest expands outward. Indrawing: lower chest sucks in — sign of severe pneumonia)\n'
        '2. RIBS: Are the ribs very prominent, pulling in between each breath?\n'
        '3. BREATHING EFFORT: Does the child appear to be working hard to breathe?\n\n'
        'NOTE: You CANNOT assess breathing rate or sounds from a photo. Only visual signs.\n\n'
        'Reply with ONLY: INDRAWING PRESENT or NO INDRAWING — then one sentence describing what you see.',
    findingKeys: ['has_indrawing'],
  ),
  'diarrhea': VisionPrompt(
    step: 'diarrhea',
    askText:
        'Can you take a close photo of your child\'s face? I want to check for dehydration signs.',
    analysisPrompt:
        'You are a child health assistant. Look at this child\'s face for dehydration signs.\n'
        'CHECK SPECIFICALLY:\n'
        '1. EYES: Are the eyes SUNKEN — appearing deeper in the sockets than normal?\n'
        '2. TEARS: When the child cries, are there tears or are the eyes dry?\n'
        '3. MOUTH/LIPS: Are the lips and mouth dry or cracked?\n'
        '4. SKIN: Does the facial skin appear dry, pale, or lacking normal elasticity?\n'
        '5. FONTANELLE: If visible (infant), is the soft spot sunken?\n\n'
        'Reply with ONLY: DEHYDRATED or NOT DEHYDRATED — then one sentence describing what you see.',
    findingKeys: ['sunken_eyes'],
  ),
  'nutrition': VisionPrompt(
    step: 'nutrition',
    askText:
        'Can you take a photo showing your child\'s body? I want to check their nutrition.',
    analysisPrompt:
        'You are a child health assistant. Look at this child\'s body for signs of malnutrition.\n'
        'CHECK SPECIFICALLY:\n'
        '1. WASTING: Is the child very thin? Are ribs, shoulder bones, or spine clearly visible?\n'
        '2. MUSCLE MASS: Are the arms and legs very thin with little muscle?\n'
        '3. FAT: Is there visible loss of fat on the buttocks (baggy pants sign)?\n'
        '4. FACE: Are the cheeks sunken (old man face)?\n'
        '5. FEET: Is there visible SWELLING in BOTH feet (bilateral edema)?\n\n'
        'Reply with ONLY: WASTING, EDEMA, BOTH, or NORMAL — then one sentence describing what you see.',
    findingKeys: ['visible_wasting', 'edema'],
  ),
};

// ============================================================================
// IMCI Question Definition
// ============================================================================

/// A single IMCI assessment question with its finding mapping.
class ImciQuestion {
  /// Unique identifier and finding key (e.g., 'has_cough', 'lethargic').
  final String id;

  /// IMCI step this question belongs to.
  final String step;

  /// The question text to ask (LLM will rephrase naturally).
  final String question;

  /// Type of expected answer.
  final AnswerType type;

  /// Only ask this question if this finding is true. Null = always ask.
  final String? triggerKey;

  /// For yes/no: the label shown on the finding chip.
  final String label;

  /// Symptom keywords. If the user's answer contains any of these,
  /// treat it as "yes" even without an explicit yes/no word.
  /// E.g., "he has cough" → contains "cough" → has_cough=true.
  final List<String> keywords;

  const ImciQuestion({
    required this.id,
    required this.step,
    required this.question,
    this.type = AnswerType.yesNo,
    this.triggerKey,
    String? label,
    this.keywords = const [],
  }) : label = label ?? id;
}

// ============================================================================
// The IMCI Question List — WHO Protocol Order
// ============================================================================

/// All IMCI questions in protocol order. Each maps to exactly one finding.
/// Conditional questions (triggerKey) are skipped if the trigger is false.
const List<ImciQuestion> imciQuestions = [
  // --- Greeting ---
  ImciQuestion(
    id: 'age_months',
    step: 'greeting',
    question: 'How old is your child in months?',
    type: AnswerType.age,
    label: 'Age',
  ),
  ImciQuestion(
    id: 'weight_kg',
    step: 'greeting',
    question: 'How much does your child weigh in kilograms? If you are not sure, that is okay — just say "not sure".',
    type: AnswerType.number,
    label: 'Weight',
  ),

  // --- Danger Signs (IMCI p.2) ---
  ImciQuestion(
    id: 'lethargic',
    step: 'danger_signs',
    question: 'Is your child very sleepy or hard to wake up?',
    label: 'Lethargic',
    keywords: ['sleepy', 'lethargic', 'drowsy', 'hard to wake', 'not alert', 'unconscious'],
  ),
  ImciQuestion(
    id: 'unable_to_drink',
    step: 'danger_signs',
    question: 'Is your child unable to drink or breastfeed?',
    label: 'Unable To Drink',
    keywords: ['unable', 'cannot', "can't", 'refuse', 'won\'t drink', 'not drinking'],
  ),
  ImciQuestion(
    id: 'vomits_everything',
    step: 'danger_signs',
    question: 'Does your child vomit everything they eat or drink?',
    label: 'Vomits Everything',
    keywords: ['vomit', 'throw up', 'throws up', 'vomiting'],
  ),
  ImciQuestion(
    id: 'has_convulsions',
    step: 'danger_signs',
    question: 'Has your child had any fits or seizures during this illness?',
    label: 'Convulsions',
    keywords: ['fit', 'seizure', 'convulsion', 'shaking', 'jerking'],
  ),

  // --- Breathing / Pneumonia (IMCI p.5) ---
  ImciQuestion(
    id: 'has_cough',
    step: 'breathing',
    question: 'Does your child have a cough or any difficulty breathing?',
    label: 'Cough',
    keywords: ['cough', 'breathing', 'wheez', 'difficult', 'noisy'],
  ),
  ImciQuestion(
    id: 'has_indrawing',
    step: 'breathing',
    question:
        'When your child breathes in, does the lower chest wall pull inward?',
    triggerKey: 'has_cough',
    label: 'Chest Indrawing',
    keywords: ['pull', 'indraw', 'suck in', 'chest pull'],
  ),
  ImciQuestion(
    id: 'has_wheeze',
    step: 'breathing',
    question:
        'Does your child make any unusual sounds when breathing, like wheezing or a harsh noise?',
    triggerKey: 'has_cough',
    label: 'Wheeze/Stridor',
    keywords: ['wheez', 'whistl', 'stridor', 'harsh', 'noisy breath'],
  ),

  // --- Diarrhea / Dehydration (IMCI p.8-9) ---
  ImciQuestion(
    id: 'has_diarrhea',
    step: 'diarrhea',
    question: 'Does your child have diarrhea or loose watery stools?',
    label: 'Diarrhea',
    keywords: ['diarrhea', 'diarrhoea', 'loose', 'watery', 'runny'],
  ),
  ImciQuestion(
    id: 'diarrhea_days',
    step: 'diarrhea',
    question: 'How many days has the diarrhea lasted?',
    type: AnswerType.number,
    triggerKey: 'has_diarrhea',
    label: 'Diarrhea Days',
  ),
  ImciQuestion(
    id: 'blood_in_stool',
    step: 'diarrhea',
    question: 'Is there any blood in the stool?',
    triggerKey: 'has_diarrhea',
    label: 'Blood In Stool',
    keywords: ['blood', 'bloody', 'red'],
  ),
  ImciQuestion(
    id: 'sunken_eyes',
    step: 'diarrhea',
    question:
        'Does your child have sunken eyes, or does the skin go back slowly when you pinch it?',
    triggerKey: 'has_diarrhea',
    label: 'Dehydration Signs',
    keywords: ['sunken', 'skin pinch', 'slow', 'dehydrat'],
  ),

  // --- Fever (IMCI p.11) ---
  ImciQuestion(
    id: 'has_fever',
    step: 'fever',
    question: 'Does your child have a fever or feel hot?',
    label: 'Fever',
    keywords: ['fever', 'hot', 'temperature', 'burning'],
  ),
  ImciQuestion(
    id: 'fever_days',
    step: 'fever',
    question: 'How many days has the fever lasted?',
    type: AnswerType.number,
    triggerKey: 'has_fever',
    label: 'Fever Days',
  ),
  ImciQuestion(
    id: 'stiff_neck',
    step: 'fever',
    question: 'Does your child have a stiff neck?',
    triggerKey: 'has_fever',
    label: 'Stiff Neck',
    keywords: ['stiff', 'neck'],
  ),
  ImciQuestion(
    id: 'malaria_risk',
    step: 'fever',
    question: 'Do you live in an area with mosquitoes or malaria?',
    triggerKey: 'has_fever',
    label: 'Malaria Risk',
    keywords: ['mosquit', 'malaria'],
  ),

  // --- Nutrition (IMCI p.14) ---
  ImciQuestion(
    id: 'visible_wasting',
    step: 'nutrition',
    question: 'Does your child look very thin? Are ribs or bones visible?',
    label: 'Visible Wasting',
    keywords: ['thin', 'ribs', 'bones', 'wast', 'malnourish'],
  ),
  ImciQuestion(
    id: 'edema',
    step: 'nutrition',
    question: "Is there any swelling in both of your child's feet?",
    label: 'Edema',
    keywords: ['swell', 'edema', 'oedema', 'puffy'],
  ),
];

/// Clinical steps in IMCI order (for progress bar).
const List<String> imciSteps = [
  'danger_signs',
  'breathing',
  'diarrhea',
  'fever',
  'nutrition',
];

// ============================================================================
// IMCI Questionnaire State
// ============================================================================

/// Manages the Q&A collection state for an IMCI assessment.
///
/// Walks through [imciQuestions] in order, skipping conditional questions
/// whose trigger is not met. Extracts findings from user answers using
/// simple, deterministic logic (no regex, no keyword matching).
class ImciQuestionnaire {
  /// Current question index.
  int _index = 0;

  /// Child's age in months.
  int ageMonths = 0;

  /// Child's weight in kg. 0 = unknown (will use age-based estimation).
  double weightKg = 0;

  /// Extracted clinical findings.
  final Map<String, dynamic> findings = {};

  /// Raw user answers keyed by question id.
  final Map<String, String> rawAnswers = {};

  /// Q&A pairs for the report (question text + user answer).
  final List<Map<String, String>> qaPairs = [];

  /// Classification results per step.
  final Map<String, DomainClassification?> classifications = {};

  ImciQuestionnaire() {
    // Initialize all boolean findings to false, numerics to 0
    for (final q in imciQuestions) {
      if (q.type == AnswerType.yesNo) {
        findings[q.id] = false;
      } else if (q.type == AnswerType.number) {
        findings[q.id] = 0;
      }
    }
  }

  /// The current question to ask, or null if assessment is complete.
  /// Automatically skips conditional questions whose trigger is false.
  ImciQuestion? get currentQuestion {
    while (_index < imciQuestions.length) {
      final q = imciQuestions[_index];
      // Skip conditional questions if trigger finding is false/absent
      if (q.triggerKey != null && findings[q.triggerKey] != true) {
        _index++;
        continue;
      }
      return q;
    }
    return null; // All questions asked
  }

  /// The step of the current question (for progress bar).
  String get currentStep {
    final q = currentQuestion;
    return q?.step ?? 'complete';
  }

  /// Progress: which clinical step are we on (1-5), 0 if greeting.
  int get stepProgress {
    final step = currentStep;
    final idx = imciSteps.indexOf(step);
    return idx >= 0 ? idx + 1 : (step == 'complete' ? imciSteps.length : 0);
  }

  /// Total questions remaining (including conditional).
  int get questionsRemaining {
    var count = 0;
    for (var i = _index; i < imciQuestions.length; i++) {
      final q = imciQuestions[i];
      if (q.triggerKey == null || findings[q.triggerKey] == true) count++;
    }
    return count;
  }

  /// Whether the assessment is complete (all questions asked).
  bool get isComplete => currentQuestion == null;

  /// Record the user's answer to the current question.
  ///
  /// Extracts the finding value from the answer text using simple,
  /// deterministic logic. No regex — just yes/no detection + number parsing.
  ///
  /// Returns the step name if a step just completed (for classification).
  String? recordAnswer(String text) {
    final q = currentQuestion;
    if (q == null) return null;

    final previousStep = q.step;

    // Store raw answer
    rawAnswers[q.id] = text;
    qaPairs.add({'question': q.question, 'answer': text, 'id': q.id});

    // Extract finding value based on question type
    switch (q.type) {
      case AnswerType.yesNo:
        // 1. Check for explicit yes/no first word
        var value = _extractYesNo(text);
        // 2. If ambiguous, check for symptom keywords in the answer
        if (value == null && q.keywords.isNotEmpty) {
          final lower = text.toLowerCase();
          for (final kw in q.keywords) {
            if (lower.contains(kw)) {
              value = true;
              break;
            }
          }
        }
        findings[q.id] = value ?? false; // Default to false if still ambiguous
      case AnswerType.number:
        final num = _extractNumber(text);
        findings[q.id] = num;
        if (q.id == 'weight_kg') {
          // 0 means "not sure" — will use age-based estimation in treatment
          weightKg = num > 0 ? num.toDouble() : 0;
        }
      case AnswerType.age:
        ageMonths = _extractAge(text);
        findings[q.id] = ageMonths;
      case AnswerType.photo:
        // Photo answers are processed separately via recordVisionAnalysis.
        // If user skips ("no photo"), just record and move on.
        rawAnswers[q.id] = text;
    }

    // Auto-fill upcoming questions from the same response.
    // E.g., "yes for last 2 days" → also fills fever_days=2.
    _autoFillFromText(text, previousStep);

    // Advance past current + any auto-filled questions
    _index++;
    while (_index < imciQuestions.length) {
      final next = imciQuestions[_index];
      if (next.step != previousStep) break;
      if (next.triggerKey != null && findings[next.triggerKey] != true) {
        _index++;
        continue;
      }
      if (rawAnswers.containsKey(next.id)) {
        _index++; // Skip — already auto-filled
        continue;
      }
      break; // This question still needs asking
    }

    // Check if the step just completed
    final nextQ = currentQuestion;
    if (nextQ == null || nextQ.step != previousStep) {
      return previousStep; // Step completed
    }
    return null;
  }

  /// Scan the user's text for answers to upcoming questions in the same step.
  /// Fills in number values and keyword-detected booleans automatically.
  void _autoFillFromText(String text, String currentStep) {
    final lower = text.toLowerCase();

    for (var i = _index + 1; i < imciQuestions.length; i++) {
      final q = imciQuestions[i];
      if (q.step != currentStep) break;
      if (q.triggerKey != null && findings[q.triggerKey] != true) continue;
      if (rawAnswers.containsKey(q.id)) continue;

      switch (q.type) {
        case AnswerType.number:
          // Don't auto-fill weight from age — they're unrelated numbers
          if (q.id == 'weight_kg') continue;
          // "yes for last 2 days" → extract the number
          final num = _extractNumber(text);
          if (num > 0) {
            findings[q.id] = num;
            rawAnswers[q.id] = text;
            qaPairs.add({
              'question': q.question,
              'answer': '(extracted: $num from "$text")',
              'id': q.id,
            });
          }
        case AnswerType.yesNo:
          // Check if keywords for this question appear in the text
          for (final kw in q.keywords) {
            if (lower.contains(kw)) {
              findings[q.id] = true;
              rawAnswers[q.id] = text;
              qaPairs.add({
                'question': q.question,
                'answer': '(detected: $kw in "$text")',
                'id': q.id,
              });
              break;
            }
          }
        case AnswerType.age:
        case AnswerType.photo:
          break;
      }
    }
  }

  /// Classify a completed step using deterministic WHO IMCI logic.
  DomainClassification? classifyStep(String step) {
    switch (step) {
      case 'danger_signs':
        final result = classifyDangerSigns(
          lethargic: findings['lethargic'] as bool? ?? false,
          unconscious: false,
          unableToDrink: findings['unable_to_drink'] as bool? ?? false,
          vomitsEverything: findings['vomits_everything'] as bool? ?? false,
          convulsions: findings['has_convulsions'] as bool? ?? false,
        );
        classifications['danger_signs'] = result;
        return result;

      case 'breathing':
        final age = ageMonths.clamp(2, 59);
        final result = classifyBreathing(
          ageMonths: age,
          hasCough: findings['has_cough'] as bool? ?? false,
          hasIndrawing: findings['has_indrawing'] as bool? ?? false,
          hasStridor: false,
          hasWheeze: findings['has_wheeze'] as bool? ?? false,
        );
        classifications['breathing'] = result;
        return result;

      case 'diarrhea':
        if (findings['has_diarrhea'] != true) {
          final result = DomainClassification(
            classification: ClassificationType.noDiarrhea,
            severity: Severity.green,
            referral: ReferralUrgency.none,
            reasoning: 'No diarrhea reported.',
          );
          classifications['diarrhea'] = result;
          return result;
        }
        final result = classifyDiarrhea(
          hasDiarrhea: true,
          durationDays: findings['diarrhea_days'] as int? ?? 0,
          bloodInStool: findings['blood_in_stool'] as bool? ?? false,
          sunkenEyes: findings['sunken_eyes'] as bool? ?? false,
          lethargic: findings['lethargic'] as bool? ?? false,
        );
        classifications['diarrhea'] = result;
        return result;

      case 'fever':
        if (findings['has_fever'] != true) {
          final result = DomainClassification(
            classification: ClassificationType.noFever,
            severity: Severity.green,
            referral: ReferralUrgency.none,
            reasoning: 'No fever reported.',
          );
          classifications['fever'] = result;
          return result;
        }
        final result = classifyFever(
          hasFever: true,
          durationDays: findings['fever_days'] as int? ?? 0,
          stiffNeck: findings['stiff_neck'] as bool? ?? false,
          malariaRisk: findings['malaria_risk'] as bool? ?? false,
        );
        classifications['fever'] = result;
        return result;

      case 'nutrition':
        final result = classifyNutrition(
          visibleWasting: findings['visible_wasting'] as bool? ?? false,
          edema: findings['edema'] as bool? ?? false,
        );
        classifications['nutrition'] = result;
        return result;

      default:
        return null;
    }
  }

  /// Overall severity across all classified steps.
  String get overallSeverity {
    final severities = classifications.values
        .where((c) => c != null)
        .map((c) => c!.severity)
        .toList();
    if (severities.contains(Severity.red)) return 'red';
    if (severities.contains(Severity.yellow)) return 'yellow';
    return 'green';
  }

  /// Build a compact summary of findings for the report LLM.
  /// Condensed to fit within 512 token limit.
  String buildReportContext() {
    final buf = StringBuffer();
    buf.write('Child $ageMonths months. ');
    buf.write('Severity: ${overallSeverity.toUpperCase()}. ');

    // Only include positive/concerning findings (compact)
    final concerns = <String>[];
    findings.forEach((key, value) {
      if (value == true) concerns.add(key.replaceAll('_', ' '));
      if (value is int && value > 0 && key.contains('days')) {
        concerns.add('$key: $value');
      }
    });
    if (concerns.isNotEmpty) {
      buf.write('Findings: ${concerns.join(', ')}. ');
    } else {
      buf.write('No concerning findings. ');
    }

    // Compact classifications
    for (final entry in classifications.entries) {
      final cls = entry.value;
      if (cls != null) {
        buf.write('${entry.key}: ${cls.severity.value}. ');
      }
    }

    return buf.toString();
  }

  // --------------------------------------------------------------------------
  // Vision Analysis — parse Gemma 4 image analysis into findings
  // --------------------------------------------------------------------------

  /// Get the vision prompt for the current photo question's step.
  VisionPrompt? get currentVisionPrompt {
    final q = currentQuestion;
    if (q == null || q.type != AnswerType.photo) return null;
    return visionPrompts[q.step];
  }

  /// Process the LLM's vision analysis response and update findings.
  ///
  /// The vision response starts with a keyword (ALERT/LETHARGIC/etc.)
  /// followed by a description. We extract the keyword to update findings.
  /// Returns the step name if the step just completed.
  String? recordVisionAnalysis(String analysisResult) {
    final q = currentQuestion;
    if (q == null || q.type != AnswerType.photo) return null;

    final previousStep = q.step;
    final vp = visionPrompts[q.step];
    if (vp == null) {
      _index++;
      final nextQ = currentQuestion;
      return (nextQ == null || nextQ.step != previousStep) ? previousStep : null;
    }

    final upper = analysisResult.toUpperCase().trim();
    rawAnswers[q.id] = analysisResult;
    qaPairs.add({
      'question': '(Photo analysis: ${q.label})',
      'answer': analysisResult,
      'id': q.id,
    });

    // Parse vision response based on step
    switch (q.step) {
      case 'danger_signs':
        if (upper.startsWith('LETHARGIC') || upper.contains('LETHARGIC')) {
          findings['lethargic'] = true;
        } else if (upper.startsWith('UNCONSCIOUS') || upper.contains('UNCONSCIOUS')) {
          findings['lethargic'] = true; // Both are danger signs
        }
        // ALERT = no change (lethargic stays as whatever text Q&A said)

      case 'breathing':
        if (upper.startsWith('INDRAWING PRESENT') || upper.contains('INDRAWING PRESENT')) {
          findings['has_indrawing'] = true;
        }

      case 'diarrhea':
        if (upper.startsWith('DEHYDRATED') ||
            (upper.contains('DEHYDRATED') && !upper.contains('NOT DEHYDRATED'))) {
          findings['sunken_eyes'] = true;
        }

      case 'nutrition':
        if (upper.contains('WASTING') && !upper.contains('NO WASTING')) {
          findings['visible_wasting'] = true;
        }
        if (upper.contains('EDEMA') && !upper.contains('NO EDEMA')) {
          findings['edema'] = true;
        }
    }
  }

  /// Skip the current photo question (user chose not to take a photo).
  String? skipPhoto() {
    final q = currentQuestion;
    if (q == null || q.type != AnswerType.photo) return null;

    final previousStep = q.step;
    rawAnswers[q.id] = '(skipped)';
    _index++;

    // Check if step completed
    final nextQ = currentQuestion;
    if (nextQ == null || nextQ.step != previousStep) {
      return previousStep;
    }
    return null;
  }

  // --------------------------------------------------------------------------
  // Answer Extraction — simple, deterministic, no regex
  // --------------------------------------------------------------------------

  /// Extract yes/no from user text. Returns null if ambiguous.
  static bool? _extractYesNo(String text) {
    final t = text.toLowerCase().trim();
    if (t.isEmpty) return null;

    // Check first word for clear yes/no
    final firstWord = t.split(RegExp(r'[\s,.]+')).first;
    const yesWords = {
      'yes', 'yeah', 'yep', 'ya', 'yah', 'sure', 'correct',
      'right', 'definitely', 'absolutely', 'true',
    };
    const noWords = {
      'no', 'nah', 'nope', 'not', 'never', 'none', 'neither',
      'false', 'negative',
    };

    if (yesWords.contains(firstWord)) return true;
    if (noWords.contains(firstWord)) return false;

    // Check for common patterns
    if (t.startsWith("he does") ||
        t.startsWith("she does") ||
        t.startsWith("they do") ||
        t.contains("has been") ||
        t.contains("is having")) {
      return true;
    }
    if (t.startsWith("he doesn") ||
        t.startsWith("she doesn") ||
        t.startsWith("they don") ||
        t.contains("has not") ||
        t.contains("is not") ||
        t.contains("hasn't") ||
        t.contains("doesn't") ||
        t.contains("don't")) {
      return false;
    }

    return null; // Ambiguous — needs LLM help
  }

  /// Extract a number from text.
  static int _extractNumber(String text) {
    // Try digit match
    final digitMatch = RegExp(r'(\d+)').firstMatch(text);
    if (digitMatch != null) {
      return int.tryParse(digitMatch.group(1)!) ?? 0;
    }

    // Try word numbers
    const wordNums = {
      'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
      'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
      'eleven': 11, 'twelve': 12, 'fourteen': 14, 'twenty': 20,
    };
    final lower = text.toLowerCase();
    for (final entry in wordNums.entries) {
      if (lower.contains(entry.key)) return entry.value;
    }

    return 0;
  }

  /// Extract age in months from text.
  static int _extractAge(String text) {
    return _extractNumber(text);
  }

  // --------------------------------------------------------------------------
  // Serialization — for persisting assessment results
  // --------------------------------------------------------------------------

  /// Serialize the complete assessment state to JSON.
  Map<String, dynamic> toJson() {
    final classMap = <String, String>{};
    for (final entry in classifications.entries) {
      if (entry.value != null) {
        classMap[entry.key] = entry.value!.classification.value;
      }
    }

    // Filter findings to only serializable types
    final serializableFindings = <String, dynamic>{};
    findings.forEach((key, value) {
      if (value is bool || value is int || value is double || value is String) {
        serializableFindings[key] = value;
      }
    });

    return {
      'ageMonths': ageMonths,
      'weightKg': weightKg,
      'severity': overallSeverity,
      'findings': serializableFindings,
      'classifications': classMap,
    };
  }
}
