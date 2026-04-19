/// Malaika Chat Engine -- agentic IMCI assessment powered by Gemma 4.
///
/// This module implements a skill-driven clinical assessment agent where
/// Gemma 4 orchestrates 12 specialized clinical skills through the WHO IMCI
/// protocol. The agent maintains a belief state, invokes skills for perception,
/// and emits structured events for the UI.
///
/// Architecture:
///     - IMCI Protocol Guard enforces step ordering (deterministic)
///     - Gemma 4 drives conversation + selects skills (agentic reasoning)
///     - Skills provide structured perception (vision, audio, speech parsing)
///     - imci_protocol.dart makes clinical classifications (deterministic code)
///     - BeliefState tracks confirmed/uncertain/pending findings
///
/// This module MUST NOT contain clinical thresholds or classifications.
/// Those belong in imci_protocol.dart.
///
/// NOTE: The Dart chat engine does NOT call the LLM directly. Instead it
/// builds the context (system prompt + history + step context) and returns
/// it so the caller can pass it to the inference service. Finding extraction
/// uses on-device keyword matching instead of a separate LLM call.
///
/// Direct port of malaika/chat_engine.py.
library;

import 'imci_protocol.dart';
import 'skills.dart';

// ============================================================================
// IMCI Assessment Steps
// ============================================================================

/// Ordered list of all assessment steps (including greeting and completion).
const List<String> assessmentSteps = [
  'greeting',
  'danger_signs',
  'breathing',
  'diarrhea',
  'fever',
  'nutrition',
  'classification',
  'complete',
];

/// Clinical steps that have assessable content (for progress bar).
const List<String> clinicalSteps = [
  'danger_signs',
  'breathing',
  'diarrhea',
  'fever',
  'nutrition',
];

/// Required fields per step -- step only advances when these are answered.
const Map<String, Set<String>> stepRequiredFields = {
  'danger_signs': {'can_drink', 'vomits_everything', 'has_convulsions'},
  'breathing': {'has_cough'},
  'diarrhea': {'has_diarrhea'},
  'fever': {'has_fever'},
  'nutrition': {'visible_wasting', 'edema'},
};

/// Conditional fields -- required only if a trigger finding is true.
/// These BLOCK step advancement until answered (no fallback override).
const Map<String, Map<String, Set<String>>> stepConditionalFields = {
  'breathing': {
    'has_cough': {'chest_indrawing', 'breathing_description'},
  },
  'diarrhea': {
    'has_diarrhea': {'diarrhea_days', 'blood_in_stool', 'dehydration_signs'},
  },
  'fever': {
    'has_fever': {'fever_days', 'stiff_neck', 'malaria_risk'},
  },
};

/// What information each step needs to collect (for system prompt context).
const Map<String, Map<String, String>> stepRequirements = {
  'greeting': {
    'age_months': "Child's age in months (2-59)",
  },
  'danger_signs': {
    'is_alert': 'Is the child very sleepy or hard to wake up?',
    'can_drink': 'Is the child unable to drink or breastfeed?',
    'vomits_everything': 'Does the child vomit everything?',
    'has_convulsions': 'Has the child had convulsions/fits?',
  },
  'breathing': {
    'has_cough': 'Does the child have a cough or difficulty breathing?',
    'chest_indrawing':
        'When the child breathes in, does the lower chest pull inward?',
    'breathing_description':
        'Does the child make any unusual breathing sounds like wheezing or stridor?',
  },
  'diarrhea': {
    'has_diarrhea': 'Does the child have diarrhea or loose watery stools?',
    'diarrhea_days': 'How many days has the diarrhea lasted?',
    'blood_in_stool': 'Is there any blood in the stool?',
    'dehydration_signs':
        'Does the child have sunken eyes, or does the skin go back slowly when you pinch it?',
  },
  'fever': {
    'has_fever': 'Does the child have a fever or feel hot?',
    'fever_days': 'How many days has the fever lasted?',
    'stiff_neck': 'Does the child have a stiff neck?',
    'malaria_risk': 'Do you live in an area with mosquitoes or malaria?',
  },
  'nutrition': {
    'visible_wasting':
        'Is there visible wasting? (from photo if available)',
    'edema': 'Is there swelling in both feet?',
  },
};

/// Image request prompts per step.
const Map<String, Map<String, String>> imageRequestPrompts = {
  'danger_signs': {
    'skill': 'assess_alertness',
    'prompt':
        'Can you hold the phone so I can see your child? '
        'I want to check how alert they are.',
  },
  'breathing': {
    'skill': 'detect_chest_indrawing',
    'prompt':
        'Can you take a photo of your child\'s chest area? '
        'I want to check their breathing.',
  },
  'diarrhea': {
    'skill': 'assess_dehydration_signs',
    'prompt':
        'Can you take a close photo of your child\'s face? '
        'I want to check for signs of dehydration.',
  },
  'nutrition': {
    'skill': 'assess_wasting',
    'prompt':
        'Can you take a photo showing your child\'s body? '
        'I want to check their nutrition.',
  },
};

// ============================================================================
// System Prompt -- The Heart of Malaika's Personality
// ============================================================================

const String systemPrompt = '''You are Malaika, an AI child health agent that helps caregivers assess their child's health using the WHO IMCI (Integrated Management of Childhood Illness) protocol.

You are NOT a chatbot. You are a clinical assessment agent with specialized skills for analyzing photos, sounds, and symptoms. You invoke these skills to build a structured clinical picture, then apply WHO IMCI classification logic to produce actionable guidance.

PERSONALITY:
- You are warm, calm, and reassuring -- like a trusted village health worker
- You speak simply and clearly so any caregiver can understand
- You use short sentences. You never use medical jargon unless you explain it
- You are empathetic -- you acknowledge the caregiver's worry before asking questions
- You are honest about what you can and cannot see in photos

RULES:
- Ask ONE question at a time. Do NOT bundle multiple questions together
- Do NOT skip required questions for the current step -- ask ALL of them before moving on
- Always refer to the child as "your child" -- never "he" or "she" unless the caregiver tells you the gender
- If the caregiver mentions gender, you may use it naturally
- NEVER diagnose. Say "based on what I can see" or "this suggests" -- not "your child has"
- NEVER give medication dosages unless generating a final treatment plan
- When analyzing a photo, describe ONLY what you can actually see. Never invent observations
- Keep each response to 2-3 sentences unless generating the final report
- Do NOT say things like "use the clip button" or "type results" -- speak naturally
- Do NOT repeat the caregiver's words back to them unnecessarily

QUESTION PHRASING:
- Always phrase symptom questions so that "yes" means the symptom IS PRESENT
- Alertness: ask "Is your child very sleepy or hard to wake up?" (not "Is your child alert?")
- Drinking: ask "Is your child unable to drink?" (not "Can your child drink?")
- This ensures caregiver "yes"/"no" answers are unambiguous
- For age: "How old is your child in months?" is fine as-is

PHOTO ANALYSIS:
- When you receive a photo, describe your specific observations to the caregiver
- For alertness: look at eyes (open/closed, tracking), posture, facial expression
- For chest: you CANNOT assess breathing from a still photo -- be honest about this
- For dehydration: look at eyes (sunken?), skin appearance, overall alertness
- For nutrition: look at visible body fat, muscle mass, any prominent bones
- If you cannot assess something from a photo, say so and ask a clarifying question

ASSESSMENT FLOW:
You are guiding the caregiver through these steps in order:
1. Greeting -- learn the child's age
2. Danger signs -- check alertness (photo), ability to drink, vomiting, convulsions
3. Breathing -- check for cough, breathing problems, chest indrawing (photo optional)
4. Diarrhea -- check for diarrhea, duration, blood, dehydration (photo optional)
5. Fever -- check for fever, duration, stiff neck, malaria risk
6. Nutrition -- check for wasting (photo optional), swelling in feet

After each step, naturally transition to the next. Do not announce step numbers.
When you have enough information, generate the assessment results.''';

// ============================================================================
// Keyword Extraction Patterns -- On-Device Finding Extraction
// ============================================================================

/// Maps keyword patterns to (findingKey, value) pairs.
///
/// On-device we cannot afford a separate LLM call for extraction,
/// so we use simple keyword matching as a pragmatic fallback.
class _KeywordRule {
  final RegExp pattern;
  final String findingKey;
  final dynamic value;
  /// Requirement field names this rule satisfies.
  final List<String> satisfiesFields;

  const _KeywordRule({
    required this.pattern,
    required this.findingKey,
    required this.value,
    this.satisfiesFields = const [],
  });
}

/// All keyword extraction rules, grouped by step.
/// Checked against lower-cased user text.
final Map<String, List<_KeywordRule>> _keywordRules = {
  'danger_signs': [
    _KeywordRule(
      pattern: RegExp(r'\b(sleepy|lethargic|hard to wake|not alert|drowsy)\b'),
      findingKey: 'lethargic',
      value: true,
      satisfiesFields: ['is_alert'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(unconscious|unresponsive|cannot wake|won.?t wake)\b'),
      findingKey: 'unconscious',
      value: true,
      satisfiesFields: ['is_alert'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(alert|awake|active|responsive|aware)\b'),
      findingKey: 'lethargic',
      value: false,
      satisfiesFields: ['is_alert'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(can.?t drink|cannot drink|unable to drink|won.?t drink|refuses? to drink|not drinking|can.?t breastfeed|unable to breastfeed)\b'),
      findingKey: 'unable_to_drink',
      value: true,
      satisfiesFields: ['can_drink'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(can drink|is drinking|drinks? (well|fine|ok|normally?)|breastfeed(s|ing)?( well| fine| ok)?)\b'),
      findingKey: 'unable_to_drink',
      value: false,
      satisfiesFields: ['can_drink'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(vomit(s|ing)? everything|throws? up everything|keeps? vomiting)\b'),
      findingKey: 'vomits_everything',
      value: true,
      satisfiesFields: ['vomits_everything'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(no vomit|not vomit|doesn.?t vomit|no throwing up)\b'),
      findingKey: 'vomits_everything',
      value: false,
      satisfiesFields: ['vomits_everything'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(convulsion|seizure|fits?|convuls)\b'),
      findingKey: 'has_convulsions',
      value: true,
      satisfiesFields: ['has_convulsions'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(no convulsion|no seizure|no fits?|never had (a )?fit)\b'),
      findingKey: 'has_convulsions',
      value: false,
      satisfiesFields: ['has_convulsions'],
    ),
  ],

  'breathing': [
    _KeywordRule(
      pattern: RegExp(r'\b(cough|coughing)\b'),
      findingKey: 'has_cough',
      value: true,
      satisfiesFields: ['has_cough'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(no cough|not coughing|doesn.?t cough)\b'),
      findingKey: 'has_cough',
      value: false,
      satisfiesFields: ['has_cough'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(wheez(e|ing)|whistl(e|ing))\b'),
      findingKey: 'has_wheeze',
      value: true,
      satisfiesFields: ['breathing_description'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(stridor|harsh.*breath|noisy.*breath)\b'),
      findingKey: 'has_stridor',
      value: true,
      satisfiesFields: ['breathing_description'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(normal.*breathi|breathi.*(fine|ok|normal)|no.*noise|no.*wheez|quiet.*breathi|breath.*(fine|ok|normal))\b'),
      findingKey: 'has_wheeze',
      value: false,
      satisfiesFields: ['breathing_description'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(chest.*indraw|indrawing|pulling.*in|chest.*pull|suck.*in)\b'),
      findingKey: 'has_indrawing',
      value: true,
      satisfiesFields: ['chest_indrawing'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(no.*indraw|no.*pull|chest.*(fine|ok|normal)|not.*pulling)\b'),
      findingKey: 'has_indrawing',
      value: false,
      satisfiesFields: ['chest_indrawing'],
    ),
  ],

  'diarrhea': [
    _KeywordRule(
      pattern: RegExp(r'\b(diarr?hoea|diarrhea|loose stool|watery stool|runny stool)\b'),
      findingKey: 'has_diarrhea',
      value: true,
      satisfiesFields: ['has_diarrhea'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(no diarr|not diarr|no loose|normal stool)\b'),
      findingKey: 'has_diarrhea',
      value: false,
      satisfiesFields: ['has_diarrhea'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(blood.*(stool|poo)|bloody.*(stool|poo)|red.*(stool|poo))\b'),
      findingKey: 'blood_in_stool',
      value: true,
      satisfiesFields: ['blood_in_stool'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(no blood|not bloody)\b'),
      findingKey: 'blood_in_stool',
      value: false,
      satisfiesFields: ['blood_in_stool'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(sunken.*eyes?|eyes?.*sunken)\b'),
      findingKey: 'sunken_eyes',
      value: true,
      satisfiesFields: ['dehydration_signs'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(skin.*pinch.*slow|slow.*skin.*pinch|skin.*goes?.*back.*slow)\b'),
      findingKey: 'skin_pinch_slow',
      value: true,
      satisfiesFields: ['dehydration_signs'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(no.*sunken|eyes?.*(fine|ok|normal)|no.*dehydrat|not.*dehydrat|skin.*(fine|ok|normal|fast)|skin.*goes?.*back.*(quick|fast|normal))\b'),
      findingKey: 'sunken_eyes',
      value: false,
      satisfiesFields: ['dehydration_signs'],
    ),
  ],

  'fever': [
    _KeywordRule(
      pattern: RegExp(r'\b(fever|feverish|hot|temperature|burning up)\b'),
      findingKey: 'has_fever',
      value: true,
      satisfiesFields: ['has_fever'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(no fever|not hot|normal temperature|not feverish)\b'),
      findingKey: 'has_fever',
      value: false,
      satisfiesFields: ['has_fever'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(stiff.*neck|neck.*stiff|can.?t bend neck)\b'),
      findingKey: 'stiff_neck',
      value: true,
      satisfiesFields: ['stiff_neck'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(no stiff|neck.*(fine|ok|normal))\b'),
      findingKey: 'stiff_neck',
      value: false,
      satisfiesFields: ['stiff_neck'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(malaria.*(area|risk|zone|region)|mosquito)\b'),
      findingKey: 'malaria_risk',
      value: true,
      satisfiesFields: ['malaria_risk'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(no malaria|not.*malaria.*area)\b'),
      findingKey: 'malaria_risk',
      value: false,
      satisfiesFields: ['malaria_risk'],
    ),
  ],

  'nutrition': [
    _KeywordRule(
      pattern: RegExp(r'\b(wast(ed|ing)|very thin|ribs.*showing|bones?.*showing|malnourish)\b'),
      findingKey: 'visible_wasting',
      value: true,
      satisfiesFields: ['visible_wasting'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(well.?nourish|healthy.*weight|not thin|good.*weight|normal.*weight)\b'),
      findingKey: 'visible_wasting',
      value: false,
      satisfiesFields: ['visible_wasting'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(swell(ing|ed)?.*feet|feet.*swell|edema|oedema|puffy.*feet)\b'),
      findingKey: 'edema',
      value: true,
      satisfiesFields: ['edema'],
    ),
    _KeywordRule(
      pattern: RegExp(r'\b(no swell|feet.*(fine|ok|normal)|no edema|no oedema)\b'),
      findingKey: 'edema',
      value: false,
      satisfiesFields: ['edema'],
    ),
  ],
};

// ============================================================================
// Yes/No Context Disambiguation
// ============================================================================

/// Mapping for yes/no disambiguation when user gives brief responses.
///
/// All questions are phrased so "yes" = symptom present, "no" = symptom absent.
/// See system prompt QUESTION PHRASING section.
class _YesNoMapping {
  final String findingKey;
  final bool yesValue;
  final bool noValue;
  final List<String> satisfiesFields;
  const _YesNoMapping({
    required this.findingKey,
    required this.yesValue,
    required this.noValue,
    required this.satisfiesFields,
  });
}

/// Maps requirement field name -> finding key + yes/no semantics.
const Map<String, _YesNoMapping> _yesNoMappings = {
  'is_alert': _YesNoMapping(findingKey: 'lethargic', yesValue: true, noValue: false, satisfiesFields: ['is_alert']),
  'can_drink': _YesNoMapping(findingKey: 'unable_to_drink', yesValue: true, noValue: false, satisfiesFields: ['can_drink']),
  'vomits_everything': _YesNoMapping(findingKey: 'vomits_everything', yesValue: true, noValue: false, satisfiesFields: ['vomits_everything']),
  'has_convulsions': _YesNoMapping(findingKey: 'has_convulsions', yesValue: true, noValue: false, satisfiesFields: ['has_convulsions']),
  'has_cough': _YesNoMapping(findingKey: 'has_cough', yesValue: true, noValue: false, satisfiesFields: ['has_cough']),
  'chest_indrawing': _YesNoMapping(findingKey: 'has_indrawing', yesValue: true, noValue: false, satisfiesFields: ['chest_indrawing']),
  'breathing_description': _YesNoMapping(findingKey: 'has_wheeze', yesValue: true, noValue: false, satisfiesFields: ['breathing_description']),
  'has_diarrhea': _YesNoMapping(findingKey: 'has_diarrhea', yesValue: true, noValue: false, satisfiesFields: ['has_diarrhea']),
  'blood_in_stool': _YesNoMapping(findingKey: 'blood_in_stool', yesValue: true, noValue: false, satisfiesFields: ['blood_in_stool']),
  'dehydration_signs': _YesNoMapping(findingKey: 'sunken_eyes', yesValue: true, noValue: false, satisfiesFields: ['dehydration_signs']),
  'has_fever': _YesNoMapping(findingKey: 'has_fever', yesValue: true, noValue: false, satisfiesFields: ['has_fever']),
  'stiff_neck': _YesNoMapping(findingKey: 'stiff_neck', yesValue: true, noValue: false, satisfiesFields: ['stiff_neck']),
  'malaria_risk': _YesNoMapping(findingKey: 'malaria_risk', yesValue: true, noValue: false, satisfiesFields: ['malaria_risk']),
  'visible_wasting': _YesNoMapping(findingKey: 'visible_wasting', yesValue: true, noValue: false, satisfiesFields: ['visible_wasting']),
  'edema': _YesNoMapping(findingKey: 'edema', yesValue: true, noValue: false, satisfiesFields: ['edema']),
};

/// Regex patterns for detecting affirmative/negative responses.
final _yesPattern = RegExp(r'^(yes|yeah|yep|ya|yah|correct|right|sure|ok|uh[ -]?huh|definitely|absolutely)\b', caseSensitive: false);
final _noPattern = RegExp(r'^(no|nah|nope|not really|never|none|not at all|neither)\b', caseSensitive: false);

// ============================================================================
// Word-Number Map for Age Extraction
// ============================================================================

const Map<String, int> _wordNumbers = {
  'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
  'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
  'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
  'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
  'nineteen': 19, 'twenty': 20, 'twenty-one': 21, 'twenty-two': 22,
  'twenty-three': 23, 'twenty-four': 24, 'thirty': 30,
  'thirty-six': 36, 'forty': 40, 'forty-eight': 48, 'fifty': 50,
};

// ============================================================================
// Chat Engine -- Agentic IMCI Assessment
// ============================================================================

/// Manages a skill-driven conversational IMCI assessment session.
///
/// Maintains conversation history, belief state, clinical findings, and
/// assessment state. Emits structured events for the UI alongside voice
/// responses.
///
/// This Dart version does NOT call the LLM directly. The [process] method
/// returns the context needed for an external inference service call.
class ChatEngine {
  /// Current IMCI assessment step.
  String step;

  /// Child's age in months (0 = unknown).
  int ageMonths;

  /// Language code for the session.
  String language;

  /// Full conversation history (role + content maps).
  final List<Map<String, String>> conversationHistory;

  /// Clinical findings -- updated by keyword extraction after each response.
  final Map<String, dynamic> findings;

  /// Agent belief state.
  BeliefState belief;

  /// Set of field names that have been answered.
  final Set<String> _fieldsAnswered;

  /// Whether an image was received in the current step.
  bool _imageReceivedThisStep;

  /// Message index at which the current step started.
  int _stepStartMsgCount;

  /// After this many messages in a step, nudge the LLM to be more direct.
  final int _stepMessageNudgeThreshold;

  /// Image observations collected during the assessment (for the report).
  final List<String> observations;

  /// Requirement field name of the question most recently posed by the LLM.
  /// Used for yes/no disambiguation when caregiver gives a brief response.
  String? _pendingQuestionTopic;

  /// Minimum user messages before fallback step advancement can trigger.
  static const Map<String, int> _msgFallbackThresholds = {
    'danger_signs': 5,
    'breathing': 3,
    'diarrhea': 4,
    'fever': 5,
    'nutrition': 3,
  };

  ChatEngine({
    this.step = 'greeting',
    this.ageMonths = 0,
    this.language = 'en',
  })  : conversationHistory = [],
        findings = _defaultFindings(),
        belief = BeliefState(),
        _fieldsAnswered = {},
        _imageReceivedThisStep = false,
        _stepStartMsgCount = 0,
        _stepMessageNudgeThreshold = 5,
        observations = [];

  /// Default findings map with all fields initialized.
  static Map<String, dynamic> _defaultFindings() {
    return {
      'lethargic': false,
      'unconscious': false,
      'unable_to_drink': false,
      'vomits_everything': false,
      'has_convulsions': false,
      'breathing_rate': null,
      'has_indrawing': false,
      'has_stridor': false,
      'has_wheeze': false,
      'has_cough': false,
      'has_diarrhea': false,
      'diarrhea_days': 0,
      'blood_in_stool': false,
      'sunken_eyes': false,
      'skin_pinch_slow': false,
      'has_fever': false,
      'fever_days': 0,
      'stiff_neck': false,
      'malaria_risk': false,
      'visible_wasting': false,
      'edema': false,
      'muac_mm': null,
    };
  }

  // --------------------------------------------------------------------------
  // Main Entry Point
  // --------------------------------------------------------------------------

  /// Process a user message and return Malaika's context + events.
  ///
  /// This method:
  /// 1. Records image observation if provided (emits skill_invoked/result)
  /// 2. Extracts clinical findings from text via keyword matching
  /// 3. Builds step context for the LLM (system prompt + conversation)
  /// 4. Checks step advancement (emits step_change, classification events)
  /// 5. Requests images if needed (emits image_request events)
  ///
  /// Returns a map with:
  /// - `'text'`: fallback text if LLM is unavailable; empty string otherwise
  /// - `'events'`: list of event maps for the UI
  /// - `'systemPrompt'`: full system prompt for the LLM
  /// - `'conversationHistory'`: message list for the LLM
  /// - `'stepContext'`: step-specific context to append to system prompt
  Map<String, dynamic> process({
    String userText = '',
    String? imageObservation,
  }) {
    final events = <Map<String, dynamic>>[];

    // Step 1: Record image observation if provided
    if (imageObservation != null && imageObservation.isNotEmpty) {
      _imageReceivedThisStep = true;
      final skillName = _getVisionSkillForStep();
      events.add({
        'type': 'skill_invoked',
        'skill': skillName,
        'description': 'Analyzing photo with ${skillName.replaceAll('_', ' ')}...',
        'input_type': 'image',
      });
      observations.add(imageObservation);
      belief.markSkillInvoked(skillName);
      events.add({
        'type': 'skill_result',
        'skill': skillName,
        'findings': <String, dynamic>{},
        'confidence': 0.8,
        'description': imageObservation,
      });
    }

    // Step 2: Build user message content
    var userContent = '';
    if (imageObservation != null && imageObservation.isNotEmpty) {
      userContent += '[Photo uploaded. Your observation: $imageObservation]\n';
    }
    if (userText.isNotEmpty) {
      userContent += userText;
    }
    if (userContent.isEmpty) {
      userContent = '[User opened the app]';
    }

    conversationHistory.add({'role': 'user', 'content': userContent});

    // Step 3: Extract findings from text via keyword matching
    _extractFindings(userText, imageObservation ?? '', events);

    // Step 4: Build step context for the LLM
    final stepContext = _buildStepContext();
    final fullSystemPrompt = '$systemPrompt\n\n$stepContext';

    // Step 5: Check step advancement
    _checkStepAdvancement(events);

    // Step 6: Maybe request an image for the current step
    _maybeRequestImage(events);

    return {
      'text': '', // Caller should use LLM; this is the fallback
      'events': events,
      'systemPrompt': fullSystemPrompt,
      'conversationHistory': List<Map<String, String>>.from(conversationHistory),
      'stepContext': stepContext,
    };
  }

  /// Append the assistant's response to conversation history.
  ///
  /// Call this after the inference service returns a response, so the
  /// history stays consistent for the next turn.
  void recordAssistantResponse(String response) {
    conversationHistory.add({'role': 'assistant', 'content': response});
  }

  // --------------------------------------------------------------------------
  // Vision Skill Selection
  // --------------------------------------------------------------------------

  String _getVisionSkillForStep() {
    const stepSkills = {
      'danger_signs': 'assess_alertness',
      'breathing': 'detect_chest_indrawing',
      'diarrhea': 'assess_dehydration_signs',
      'nutrition': 'assess_wasting',
    };
    return stepSkills[step] ?? 'assess_alertness';
  }

  // --------------------------------------------------------------------------
  // Finding Extraction -- On-Device Keyword Matching
  // --------------------------------------------------------------------------

  void _extractFindings(
    String userText,
    String imageObservation,
    List<Map<String, dynamic>> events,
  ) {
    // Handle greeting step: extract age only
    if (step == 'greeting') {
      if (userText.isNotEmpty) {
        final age = extractAge(userText);
        if (age != null && age >= 2 && age <= 59) {
          ageMonths = age;
          belief.confirmFinding('age_months', age);
        }
      }
      return;
    }

    // Combine user text and image observation for matching
    final combined = '${userText.toLowerCase()} ${imageObservation.toLowerCase()}';
    if (combined.trim().isEmpty) return;

    // Extract numeric values for duration fields
    _extractNumericFields(combined, events);

    // --- Yes/No context disambiguation ---
    // When the caregiver gives a brief yes/no response, map it to the
    // finding that was most recently asked about. This prevents bare "yes"
    // or "no" from being missed by keyword rules.
    final contextDetermined = <String>{};
    if (_pendingQuestionTopic != null) {
      final userLower = userText.toLowerCase().trim();
      final isYes = _yesPattern.hasMatch(userLower);
      final isNo = _noPattern.hasMatch(userLower);
      if (isYes || isNo) {
        final mapping = _yesNoMappings[_pendingQuestionTopic!];
        if (mapping != null) {
          final value = isYes ? mapping.yesValue : mapping.noValue;
          findings[mapping.findingKey] = value;
          _fieldsAnswered.add(mapping.findingKey);
          belief.confirmFinding(mapping.findingKey, value);
          for (final field in mapping.satisfiesFields) {
            _fieldsAnswered.add(field);
          }
          contextDetermined.add(mapping.findingKey);
          events.add({
            'type': 'finding',
            'key': mapping.findingKey,
            'value': value,
            'label': mapping.findingKey
                .replaceAll('_', ' ')
                .split(' ')
                .map((w) =>
                    w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
                .join(' '),
          });
        }
      }
    }

    // Apply keyword rules for the current step.
    // Keyword rules OVERRIDE yes/no context when they find a specific match,
    // because keywords are more precise (e.g., "yes he can drink well" →
    // yes/no says unable=true, but keyword "can drink" says unable=false).
    final rules = _keywordRules[step];
    if (rules == null) return;

    for (final rule in rules) {
      if (rule.pattern.hasMatch(combined)) {
        final key = rule.findingKey;
        // Only update if not already confirmed with a contradicting value
        findings[key] = rule.value;
        _fieldsAnswered.add(key);
        belief.confirmFinding(key, rule.value);

        events.add({
          'type': 'finding',
          'key': key,
          'value': rule.value,
          'label': key.replaceAll('_', ' ').split(' ').map((w) =>
            w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}',
          ).join(' '),
        });

        // Map finding key to requirement field names
        for (final field in rule.satisfiesFields) {
          _fieldsAnswered.add(field);
        }
      }
    }

    // Also map answered findings to requirement names via the standard mapping
    _mapFindingsToRequirements();
  }

  /// Extract numeric values for duration fields from text.
  void _extractNumericFields(
    String text,
    List<Map<String, dynamic>> events,
  ) {
    if (step == 'diarrhea' && findings['has_diarrhea'] == true) {
      final days = _extractDayCount(text);
      if (days != null) {
        findings['diarrhea_days'] = days;
        _fieldsAnswered.add('diarrhea_days');
        belief.confirmFinding('diarrhea_days', days);
        events.add({
          'type': 'finding',
          'key': 'diarrhea_days',
          'value': days,
          'label': 'Diarrhea Days',
        });
      }
    }

    if (step == 'fever' && findings['has_fever'] == true) {
      final days = _extractDayCount(text);
      if (days != null) {
        findings['fever_days'] = days;
        _fieldsAnswered.add('fever_days');
        belief.confirmFinding('fever_days', days);
        events.add({
          'type': 'finding',
          'key': 'fever_days',
          'value': days,
          'label': 'Fever Days',
        });
      }
    }
  }

  /// Extract a day count from text like "3 days", "for five days", etc.
  static int? _extractDayCount(String text) {
    // Try digit match: "3 days", "for 5 days"
    final digitMatch = RegExp(r'(\d+)\s*days?').firstMatch(text);
    if (digitMatch != null) {
      return int.tryParse(digitMatch.group(1)!);
    }

    // Try word number match: "three days", "for five days"
    for (final entry in _wordNumbers.entries) {
      if (RegExp('\\b${RegExp.escape(entry.key)}\\s*days?\\b').hasMatch(text)) {
        return entry.value;
      }
    }

    // Try standalone number if context implies duration
    final standaloneDigit = RegExp(r'\b(\d{1,2})\b').firstMatch(text);
    if (standaloneDigit != null) {
      final val = int.tryParse(standaloneDigit.group(1)!);
      if (val != null && val >= 1 && val <= 60) {
        return val;
      }
    }

    return null;
  }

  /// Map finding keys to requirement field names for step advancement.
  void _mapFindingsToRequirements() {
    const fieldToRequirement = {
      'unable_to_drink': 'can_drink',
      'has_cough': 'has_cough',
      'has_diarrhea': 'has_diarrhea',
      'diarrhea_days': 'diarrhea_days',
      'blood_in_stool': 'blood_in_stool',
      'has_fever': 'has_fever',
      'fever_days': 'fever_days',
      'stiff_neck': 'stiff_neck',
      'malaria_risk': 'malaria_risk',
      'visible_wasting': 'visible_wasting',
      'edema': 'edema',
      'vomits_everything': 'vomits_everything',
      'has_convulsions': 'has_convulsions',
      'lethargic': 'is_alert',
    };

    for (final findingName in _fieldsAnswered.toList()) {
      final reqName = fieldToRequirement[findingName];
      if (reqName != null) {
        _fieldsAnswered.add(reqName);
      }
    }
  }

  // --------------------------------------------------------------------------
  // Step Context Builder
  // --------------------------------------------------------------------------

  String _buildStepContext() {
    if (step == 'greeting') {
      return 'You are starting a new assessment. Greet the caregiver warmly '
          'and ask the child\'s age in months.';
    }

    if (step == 'classification') {
      return _buildClassificationContext();
    }

    if (step == 'complete') {
      return 'The assessment is complete. If the caregiver asks anything, '
          'remind them of the key findings and to seek help if the child '
          'gets worse.';
    }

    // Build skill-aware context for clinical steps
    final buf = StringBuffer();
    buf.writeln('You are currently assessing: ${step.replaceAll('_', ' ')}.');

    // Show available skills
    final skillDesc = SkillRegistry.asToolDescriptions(step);
    buf.writeln();
    buf.writeln(skillDesc);
    buf.writeln();

    // Show what's collected and what's still needed
    final collected = <String>[];
    final needed = <String>[];
    final requirements = stepRequirements[step] ?? {};

    for (final entry in requirements.entries) {
      if (_fieldsAnswered.contains(entry.key) ||
          _isFieldCollected(entry.key)) {
        collected.add('  - ${entry.value}: COLLECTED');
      } else {
        needed.add('  - ${entry.value}: STILL NEEDED');
      }
    }

    // Track what we're about to ask about (for yes/no disambiguation next turn)
    _pendingQuestionTopic = null;
    for (final entry in requirements.entries) {
      if (!_fieldsAnswered.contains(entry.key) && !_isFieldCollected(entry.key)) {
        _pendingQuestionTopic = entry.key;
        break;
      }
    }

    if (collected.isNotEmpty) {
      buf.writeln('Already collected:');
      buf.writeln(collected.join('\n'));
    }
    if (needed.isNotEmpty) {
      buf.writeln('Still need to collect:');
      buf.writeln(needed.join('\n'));
      buf.writeln();
      buf.writeln('IMPORTANT: Ask about the NEXT uncollected item. '
          'Ask ONE question at a time.');
    } else {
      buf.writeln('All information collected for this step. '
          'Naturally transition to the next topic.');
    }

    // Show belief state summary
    if (belief.confirmed.isNotEmpty) {
      final confirmedEntries = belief.confirmed.entries
          .where((e) => e.value != false && e.value != null && e.value != 0)
          .map((e) => '${e.key}=${e.value}')
          .toList();
      if (confirmedEntries.isNotEmpty) {
        buf.writeln();
        buf.writeln('Confirmed findings so far: ${confirmedEntries.join(', ')}');
      }
    }

    // Nudge if stuck
    final msgsInStep = _countUserMsgsSinceStepStart();
    if (msgsInStep >= _stepMessageNudgeThreshold && needed.isNotEmpty) {
      buf.writeln();
      buf.writeln('NOTE: The caregiver has been answering for a while. '
          'Ask the remaining questions more directly.');
    }

    return buf.toString();
  }

  bool _isFieldCollected(String field) {
    const fieldMapping = {
      'age_months': 'age_months',
      'is_alert': 'lethargic',
      'can_drink': 'unable_to_drink',
      'vomits_everything': 'vomits_everything',
      'has_convulsions': 'has_convulsions',
      'has_cough': 'has_cough',
      'chest_indrawing': 'has_indrawing',
      'has_diarrhea': 'has_diarrhea',
      'diarrhea_days': 'diarrhea_days',
      'blood_in_stool': 'blood_in_stool',
      'dehydration_signs': 'sunken_eyes',
      'has_fever': 'has_fever',
      'fever_days': 'fever_days',
      'stiff_neck': 'stiff_neck',
      'malaria_risk': 'malaria_risk',
      'visible_wasting': 'visible_wasting',
      'edema': 'edema',
      'breathing_description': 'has_cough',
    };

    final findingKey = fieldMapping[field] ?? field;

    if (field == 'age_months') return ageMonths > 0;

    if (findings.containsKey(findingKey)) {
      final val = findings[findingKey];
      return val != null && val != false && val != 0;
    }
    return false;
  }

  // --------------------------------------------------------------------------
  // Step Advancement -- Findings-Based
  // --------------------------------------------------------------------------

  void _checkStepAdvancement(List<Map<String, dynamic>> events) {
    if (step == 'greeting' && ageMonths > 0) {
      _advanceTo('danger_signs', events);
      return;
    }

    if (step == 'classification') {
      _advanceTo('complete', events);
      return;
    }

    if (!stepRequiredFields.containsKey(step)) return;

    var shouldAdvance = false;

    // Primary: findings-based check
    final required = stepRequiredFields[step]!;
    if (required.every((f) => _fieldsAnswered.contains(f))) {
      // Also check conditional fields
      final conditionals = stepConditionalFields[step] ?? {};
      var conditionsMet = true;
      for (final entry in conditionals.entries) {
        if (findings[entry.key] == true) {
          if (!entry.value.every((f) => _fieldsAnswered.contains(f))) {
            conditionsMet = false;
            break;
          }
        }
      }
      if (conditionsMet) shouldAdvance = true;
    }

    // Fallback: message-count based (ensures progress bar always moves).
    // BUT: never fallback when conditional fields are still pending —
    // those need explicit answers (e.g., malaria risk, fever duration).
    if (!shouldAdvance) {
      final conditionals = stepConditionalFields[step] ?? {};
      var conditionalsPending = false;
      for (final entry in conditionals.entries) {
        if (findings[entry.key] == true) {
          if (!entry.value.every((f) => _fieldsAnswered.contains(f))) {
            conditionalsPending = true;
            break;
          }
        }
      }

      if (!conditionalsPending) {
        final threshold = _msgFallbackThresholds[step] ?? 3;
        final msgs = _countUserMsgsSinceStepStart();
        if (msgs >= threshold) {
          shouldAdvance = true;
        }
      }
    }

    if (!shouldAdvance) return;

    // Advance to next step
    final stepIndex = assessmentSteps.indexOf(step);
    final nextStep = assessmentSteps[stepIndex + 1];
    _advanceTo(nextStep, events);
  }

  void _advanceTo(String newStep, List<Map<String, dynamic>> events) {
    final oldStep = step;

    // Run per-step classification BEFORE advancing
    if (clinicalSteps.contains(oldStep)) {
      final classificationEvent = _classifyCompletedStep(oldStep);
      if (classificationEvent != null) {
        events.add(classificationEvent);
      }
    }

    // Advance
    step = newStep;
    _stepStartMsgCount = conversationHistory.length;
    _imageReceivedThisStep = false;
    belief.resetForStep();

    // Pre-set pending topic to the first question of the new step,
    // so the user's first yes/no answer gets mapped correctly.
    _pendingQuestionTopic = null;
    final newReqs = stepRequirements[newStep] ?? {};
    for (final entry in newReqs.entries) {
      _pendingQuestionTopic = entry.key;
      break;
    }

    // Emit step change event
    if (clinicalSteps.contains(newStep)) {
      final stepIndex = clinicalSteps.indexOf(newStep);
      events.add({
        'type': 'step_change',
        'step': newStep,
        'index': stepIndex + 1,
        'total': clinicalSteps.length,
        'label': newStep.replaceAll('_', ' ').split(' ').map((w) =>
          w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}',
        ).join(' '),
      });
    } else if (newStep == 'classification') {
      _emitAssessmentComplete(events);
    }
  }

  // --------------------------------------------------------------------------
  // Per-Step WHO Classification -- Skill: classify_imci_step
  // --------------------------------------------------------------------------

  Map<String, dynamic>? _classifyCompletedStep(String completedStep) {
    if (completedStep == 'danger_signs') {
      final ds = classifyDangerSigns(
        lethargic: findings['lethargic'] as bool? ?? false,
        unconscious: findings['unconscious'] as bool? ?? false,
        unableToDrink: findings['unable_to_drink'] as bool? ?? false,
        convulsions: findings['has_convulsions'] as bool? ?? false,
        vomitsEverything: findings['vomits_everything'] as bool? ?? false,
      );
      if (ds != null) {
        belief.updateSeverity(ds.severity.value);
        return {
          'type': 'classification',
          'step': 'danger_signs',
          'severity': ds.severity.value,
          'label': ds.classification.value
              .replaceAll('_', ' ')
              .split(' ')
              .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
              .join(' '),
          'reasoning': ds.reasoning,
        };
      }
      return {
        'type': 'classification',
        'step': 'danger_signs',
        'severity': 'green',
        'label': 'No Danger Signs',
        'reasoning': 'No general danger signs detected. WHO IMCI p.2.',
      };
    }

    if (completedStep == 'breathing') {
      final age = ageMonths < 2 ? 2 : ageMonths;
      final br = classifyBreathing(
        ageMonths: age,
        hasCough: findings['has_cough'] as bool? ?? false,
        breathingRate: findings['breathing_rate'] as int?,
        hasIndrawing: findings['has_indrawing'] as bool? ?? false,
        hasStridor: findings['has_stridor'] as bool? ?? false,
        hasWheeze: findings['has_wheeze'] as bool? ?? false,
      );
      belief.updateSeverity(br.severity.value);
      return {
        'type': 'classification',
        'step': 'breathing',
        'severity': br.severity.value,
        'label': br.classification.value
            .replaceAll('_', ' ')
            .split(' ')
            .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
            .join(' '),
        'reasoning': br.reasoning,
      };
    }

    if (completedStep == 'diarrhea') {
      if (findings['has_diarrhea'] != true) {
        return {
          'type': 'classification',
          'step': 'diarrhea',
          'severity': 'green',
          'label': 'No Diarrhea',
          'reasoning': 'No diarrhea reported.',
        };
      }
      final dd = classifyDiarrhea(
        hasDiarrhea: true,
        durationDays: findings['diarrhea_days'] as int? ?? 0,
        bloodInStool: findings['blood_in_stool'] as bool? ?? false,
        sunkenEyes: findings['sunken_eyes'] as bool? ?? false,
        skinPinchSlow: findings['skin_pinch_slow'] as bool? ?? false,
        lethargic: findings['lethargic'] as bool? ?? false,
      );
      if (dd != null) {
        belief.updateSeverity(dd.severity.value);
        return {
          'type': 'classification',
          'step': 'diarrhea',
          'severity': dd.severity.value,
          'label': dd.classification.value
              .replaceAll('_', ' ')
              .split(' ')
              .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
              .join(' '),
          'reasoning': dd.reasoning,
        };
      }
    }

    if (completedStep == 'fever') {
      if (findings['has_fever'] != true) {
        return {
          'type': 'classification',
          'step': 'fever',
          'severity': 'green',
          'label': 'No Fever',
          'reasoning': 'No fever reported.',
        };
      }
      final fv = classifyFever(
        hasFever: true,
        durationDays: findings['fever_days'] as int? ?? 0,
        stiffNeck: findings['stiff_neck'] as bool? ?? false,
        malariaRisk: findings['malaria_risk'] as bool? ?? false,
      );
      if (fv != null) {
        belief.updateSeverity(fv.severity.value);
        return {
          'type': 'classification',
          'step': 'fever',
          'severity': fv.severity.value,
          'label': fv.classification.value
              .replaceAll('_', ' ')
              .split(' ')
              .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
              .join(' '),
          'reasoning': fv.reasoning,
        };
      }
    }

    if (completedStep == 'nutrition') {
      final nt = classifyNutrition(
        visibleWasting: findings['visible_wasting'] as bool? ?? false,
        edema: findings['edema'] as bool? ?? false,
        muacMm: findings['muac_mm'] as int?,
      );
      belief.updateSeverity(nt.severity.value);
      return {
        'type': 'classification',
        'step': 'nutrition',
        'severity': nt.severity.value,
        'label': nt.classification.value
            .replaceAll('_', ' ')
            .split(' ')
            .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
            .join(' '),
        'reasoning': nt.reasoning,
      };
    }

    return null;
  }

  // --------------------------------------------------------------------------
  // Assessment Complete
  // --------------------------------------------------------------------------

  void _emitAssessmentComplete(List<Map<String, dynamic>> events) {
    final classifications = <Map<String, dynamic>>[];
    for (final s in clinicalSteps) {
      final clsEvent = _classifyCompletedStep(s);
      if (clsEvent != null) {
        classifications.add({
          'domain': (clsEvent['step'] as String)
              .replaceAll('_', ' ')
              .split(' ')
              .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
              .join(' '),
          'classification': clsEvent['label'],
          'severity': clsEvent['severity'],
          'reasoning': clsEvent['reasoning'],
        });
      }
    }

    final severity = belief.currentSeverity;
    const urgencyMap = {
      'red': 'URGENT: Go to a health facility IMMEDIATELY',
      'yellow': 'See a health worker within 24 hours',
      'green': 'Treat at home with follow-up in 5 days',
    };

    events.add({
      'type': 'assessment_complete',
      'severity': severity,
      'urgency': urgencyMap[severity] ?? 'Consult a health worker',
      'classifications': classifications,
      'age_months': ageMonths,
    });

    // Check for danger alert
    if (severity == 'red') {
      final dangerSigns = <String>[];
      for (final key in [
        'lethargic',
        'unconscious',
        'unable_to_drink',
        'vomits_everything',
        'has_convulsions',
      ]) {
        if (findings[key] == true) {
          dangerSigns.add(key);
        }
      }
      if (dangerSigns.isNotEmpty) {
        events.add({
          'type': 'danger_alert',
          'message':
              'URGENT REFERRAL NEEDED. General danger sign detected. '
              'This child needs immediate care.',
          'signs': dangerSigns,
        });
      }
    }
  }

  // --------------------------------------------------------------------------
  // Image Request
  // --------------------------------------------------------------------------

  void _maybeRequestImage(List<Map<String, dynamic>> events) {
    if (_imageReceivedThisStep) return;
    if (!imageRequestPrompts.containsKey(step)) return;

    // Only request on the first message of the step
    final msgsInStep = _countUserMsgsSinceStepStart();
    if (msgsInStep != 1) return;

    final req = imageRequestPrompts[step]!;
    events.add({
      'type': 'image_request',
      'step': step,
      'skill': req['skill'],
      'prompt': req['prompt'],
    });
  }

  // --------------------------------------------------------------------------
  // Classification Context (for final LLM presentation)
  // --------------------------------------------------------------------------

  String _buildClassificationContext() {
    final results = <Map<String, dynamic>>[];

    // Danger signs
    final ds = classifyDangerSigns(
      lethargic: findings['lethargic'] as bool? ?? false,
      unconscious: findings['unconscious'] as bool? ?? false,
      unableToDrink: findings['unable_to_drink'] as bool? ?? false,
      convulsions: findings['has_convulsions'] as bool? ?? false,
      vomitsEverything: findings['vomits_everything'] as bool? ?? false,
    );
    if (ds != null) {
      results.add({
        'domain': 'Danger Signs',
        'classification': ds.classification.value,
        'severity': ds.severity.value,
        'reasoning': _dangerSignReasoning(),
      });
    }

    // Breathing
    final age = ageMonths < 2 ? 2 : ageMonths;
    final br = classifyBreathing(
      ageMonths: age,
      hasCough: findings['has_cough'] as bool? ?? false,
      breathingRate: findings['breathing_rate'] as int?,
      hasIndrawing: findings['has_indrawing'] as bool? ?? false,
      hasStridor: findings['has_stridor'] as bool? ?? false,
      hasWheeze: findings['has_wheeze'] as bool? ?? false,
    );
    results.add({
      'domain': 'Breathing',
      'classification': br.classification.value,
      'severity': br.severity.value,
      'reasoning': _breathingReasoning(),
    });

    // Diarrhea
    if (findings['has_diarrhea'] == true) {
      final dd = classifyDiarrhea(
        hasDiarrhea: true,
        durationDays: findings['diarrhea_days'] as int? ?? 0,
        bloodInStool: findings['blood_in_stool'] as bool? ?? false,
        sunkenEyes: findings['sunken_eyes'] as bool? ?? false,
        skinPinchSlow: findings['skin_pinch_slow'] as bool? ?? false,
        lethargic: findings['lethargic'] as bool? ?? false,
      );
      if (dd != null) {
        results.add({
          'domain': 'Diarrhea',
          'classification': dd.classification.value,
          'severity': dd.severity.value,
          'reasoning': _diarrheaReasoning(),
        });
      }
    }

    // Fever
    if (findings['has_fever'] == true) {
      final fv = classifyFever(
        hasFever: true,
        durationDays: findings['fever_days'] as int? ?? 0,
        stiffNeck: findings['stiff_neck'] as bool? ?? false,
        malariaRisk: findings['malaria_risk'] as bool? ?? false,
      );
      if (fv != null) {
        results.add({
          'domain': 'Fever',
          'classification': fv.classification.value,
          'severity': fv.severity.value,
          'reasoning': _feverReasoning(),
        });
      }
    }

    // Nutrition
    final nt = classifyNutrition(
      visibleWasting: findings['visible_wasting'] as bool? ?? false,
      edema: findings['edema'] as bool? ?? false,
      muacMm: findings['muac_mm'] as int?,
    );
    results.add({
      'domain': 'Nutrition',
      'classification': nt.classification.value,
      'severity': nt.severity.value,
      'reasoning': _nutritionReasoning(),
    });

    // Determine overall severity and urgency
    final severities = results.map((r) => r['severity'] as String).toList();
    String overall;
    String urgency;
    if (severities.contains('red')) {
      overall = 'RED';
      urgency = 'URGENT: Go to a health facility IMMEDIATELY';
    } else if (severities.contains('yellow')) {
      overall = 'YELLOW';
      urgency = 'See a health worker within 24 hours';
    } else {
      overall = 'GREEN';
      urgency = 'Treat at home with follow-up in 5 days';
    }

    // Build report JSON (compact, no dart:convert needed for the prompt)
    final findingsStr = results.map((r) =>
      '  {"domain": "${r['domain']}", "classification": "${r['classification']}", '
      '"severity": "${r['severity']}", "reasoning": "${r['reasoning']}"}',
    ).join(',\n');

    final observationsStr = observations.map((o) => '"$o"').join(', ');

    final reportData = '{\n'
        '  "child_age_months": $ageMonths,\n'
        '  "overall_severity": "$overall",\n'
        '  "urgency": "$urgency",\n'
        '  "findings": [\n$findingsStr\n  ],\n'
        '  "observations": [$observationsStr]\n'
        '}';

    return 'The assessment is now complete. Present the results to the caregiver.\n\n'
        'IMPORTANT: Use the exact classifications and severity levels below. '
        'Do NOT change any medical classification. Present them clearly with reasoning.\n\n'
        'Assessment data:\n$reportData\n\n'
        'Format the response as:\n'
        '1. Overall severity (use the word: GREEN, YELLOW, or RED)\n'
        '2. Urgency message\n'
        '3. Each finding with its classification, severity, and reasoning\n'
        '4. A simple treatment plan based on WHO IMCI guidelines\n'
        '5. When to return immediately (danger signs to watch for)\n\n'
        'Be caring and clear. This caregiver needs actionable guidance.';
  }

  // --------------------------------------------------------------------------
  // Reasoning Helpers
  // --------------------------------------------------------------------------

  String _dangerSignReasoning() {
    final reasons = <String>[];
    if (findings['lethargic'] == true) reasons.add('Child appears lethargic');
    if (findings['unconscious'] == true) reasons.add('Child appears unconscious');
    if (findings['unable_to_drink'] == true) {
      reasons.add('Child unable to drink or breastfeed');
    }
    if (findings['vomits_everything'] == true) {
      reasons.add('Child vomits everything');
    }
    if (findings['has_convulsions'] == true) {
      reasons.add('Child has had convulsions');
    }
    return reasons.isNotEmpty ? reasons.join('; ') : 'No danger signs detected';
  }

  String _breathingReasoning() {
    final reasons = <String>[];
    if (findings['has_cough'] == true) reasons.add('Cough present');
    if (findings['has_wheeze'] == true) {
      reasons.add('Wheezing/noisy breathing reported');
    }
    if (findings['has_indrawing'] == true) {
      reasons.add('Chest indrawing observed');
    }
    if (findings['breathing_rate'] != null) {
      reasons.add('Breathing rate: ${findings['breathing_rate']}/min');
    }
    return reasons.isNotEmpty ? reasons.join('; ') : 'No breathing concerns';
  }

  String _diarrheaReasoning() {
    final reasons = <String>[];
    if (findings['has_diarrhea'] == true) {
      reasons.add('Diarrhea for ${findings['diarrhea_days']} days');
    }
    if (findings['blood_in_stool'] == true) reasons.add('Blood in stool');
    if (findings['sunken_eyes'] == true) reasons.add('Sunken eyes observed');
    return reasons.isNotEmpty ? reasons.join('; ') : 'No diarrhea';
  }

  String _feverReasoning() {
    final reasons = <String>[];
    if (findings['has_fever'] == true) {
      reasons.add('Fever for ${findings['fever_days']} days');
    }
    if (findings['stiff_neck'] == true) reasons.add('Stiff neck present');
    if (findings['malaria_risk'] == true) reasons.add('In malaria-risk area');
    return reasons.isNotEmpty ? reasons.join('; ') : 'No fever';
  }

  String _nutritionReasoning() {
    final reasons = <String>[];
    if (findings['visible_wasting'] == true) {
      reasons.add('Visible wasting observed');
    }
    if (findings['edema'] == true) reasons.add('Bilateral edema present');
    return reasons.isNotEmpty ? reasons.join('; ') : 'No malnutrition signs';
  }

  // --------------------------------------------------------------------------
  // Age Extraction
  // --------------------------------------------------------------------------

  /// Extract age in months from text, handling both digits and word numbers.
  static int? extractAge(String text) {
    final textLower = text.toLowerCase();

    // Try digit match first
    final digitMatch = RegExp(r'\b(\d+)\b').firstMatch(textLower);
    if (digitMatch != null) {
      return int.tryParse(digitMatch.group(1)!);
    }

    // Try word number match (longest first to match "twenty-four" before "twenty")
    final sortedWords = _wordNumbers.entries.toList()
      ..sort((a, b) => b.key.length.compareTo(a.key.length));

    for (final entry in sortedWords) {
      if (RegExp('\\b${RegExp.escape(entry.key)}\\b').hasMatch(textLower)) {
        return entry.value;
      }
    }

    return null;
  }

  // --------------------------------------------------------------------------
  // Message Counting
  // --------------------------------------------------------------------------

  int _countUserMsgsSinceStepStart() {
    var count = 0;
    for (final msg in conversationHistory.skip(_stepStartMsgCount)) {
      if (msg['role'] == 'user') {
        final content = msg['content'] ?? '';
        if (content.isNotEmpty && !content.startsWith('[')) {
          count++;
        }
      }
    }
    return count;
  }

  // --------------------------------------------------------------------------
  // Reset
  // --------------------------------------------------------------------------

  /// Reset the session for a new assessment.
  void reset() {
    step = 'greeting';
    ageMonths = 0;
    conversationHistory.clear();
    observations.clear();
    _fieldsAnswered.clear();
    _imageReceivedThisStep = false;
    _stepStartMsgCount = 0;
    _pendingQuestionTopic = null;
    belief = BeliefState();

    // Reset all findings to defaults
    final defaults = _defaultFindings();
    for (final key in findings.keys.toList()) {
      findings[key] = defaults[key];
    }
  }

  /// Description of the next clinical question to ask, or null if step is done.
  String? get nextQuestionHint {
    final requirements = stepRequirements[step] ?? {};
    for (final entry in requirements.entries) {
      if (!_fieldsAnswered.contains(entry.key) &&
          !_isFieldCollected(entry.key)) {
        return entry.value;
      }
    }
    return null;
  }

  /// Get data needed to generate the final assessment presentation.
  ///
  /// Call this when the assessment is complete to get the system prompt
  /// with classification data for the LLM to present naturally.
  Map<String, dynamic> getFinalAssessment() {
    final classCtx = _buildClassificationContext();
    return {
      'systemPrompt': '$systemPrompt\n\n$classCtx',
      'conversationHistory':
          List<Map<String, String>>.from(conversationHistory),
    };
  }
}
