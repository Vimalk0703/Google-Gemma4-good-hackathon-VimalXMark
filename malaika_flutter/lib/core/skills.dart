/// Malaika Skills Registry -- Clinical skill definitions for the IMCI agent.
///
/// Each skill is a structured tool that Gemma 4 can reason about and invoke
/// during the IMCI assessment. Skills provide:
/// - Typed input/output contracts
/// - Human-readable descriptions for the LLM context
/// - Mapping to IMCI protocol steps
/// - Execution results with confidence and followup suggestions
///
/// Architecture:
///     - Skills define WHAT can be done (declarative)
///     - ChatEngine decides WHEN to invoke each skill (agentic reasoning)
///     - imci_protocol.dart decides WHAT the findings mean (deterministic)
///     - Gemma 4 does the actual perception work (vision, audio, speech)
///
/// This module MUST NOT contain inference logic or model calls.
///
/// Direct port of malaika/skills.py.
library;

import 'package:flutter/foundation.dart';

// ============================================================================
// Skill Definition
// ============================================================================

/// A clinical assessment skill that the IMCI agent can invoke.
///
/// Each skill maps to a specific perception or reasoning capability
/// backed by Gemma 4. Skills are organized by IMCI protocol step.
@immutable
class Skill {
  /// Unique skill identifier (e.g. "assess_alertness").
  final String name;

  /// What this skill does (shown to Gemma 4 for reasoning).
  final String description;

  /// Which IMCI step this skill belongs to ("danger_signs", "any", etc.).
  final String imciStep;

  /// Primary input modality ("image", "audio", "text", "video", "findings").
  final String inputType;

  /// Parameter name -> description mapping.
  final Map<String, String> parameters;

  /// Return field name -> description mapping.
  final Map<String, String> returns;

  /// Whether this skill needs camera/mic input from caregiver.
  final bool requiresMedia;

  /// What to tell the caregiver if media is needed.
  final String mediaPrompt;

  const Skill({
    required this.name,
    required this.description,
    required this.imciStep,
    required this.inputType,
    required this.parameters,
    required this.returns,
    this.requiresMedia = false,
    this.mediaPrompt = '',
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) || (other is Skill && other.name == name);

  @override
  int get hashCode => name.hashCode;
}

// ============================================================================
// Skill Execution Result
// ============================================================================

/// Result of executing a clinical skill.
class SkillResult {
  /// Which skill produced this result.
  final String skillName;

  /// Whether the skill executed without error.
  bool success;

  /// Structured findings dict (e.g. {"lethargic": true}).
  Map<String, dynamic> findings;

  /// Human-readable summary of what was observed.
  String description;

  /// Confidence score 0.0-1.0.
  double confidence;

  /// Whether the agent should ask a clarifying question.
  bool requiresFollowup;

  /// Suggested followup if needed.
  String followupSuggestion;

  SkillResult({
    required this.skillName,
    this.success = false,
    Map<String, dynamic>? findings,
    this.description = '',
    this.confidence = 0.0,
    this.requiresFollowup = false,
    this.followupSuggestion = '',
  }) : findings = findings ?? {};
}

// ============================================================================
// Belief State -- What the Agent Knows
// ============================================================================

/// Tracks what the IMCI agent knows, what's uncertain, and what's pending.
///
/// Updated after each skill execution and caregiver response.
/// Used by ChatEngine to decide what to ask/do next.
class BeliefState {
  /// Findings confirmed by skills or user responses.
  final Map<String, dynamic> confirmed;

  /// Findings with low confidence -- key -> reason string.
  final Map<String, String> uncertain;

  /// Questions the agent still needs to ask.
  final List<String> pendingQuestions;

  /// Skills already executed in the current step.
  final List<String> skillsInvoked;

  /// Running worst-case severity across all steps.
  String currentSeverity;

  BeliefState({
    Map<String, dynamic>? confirmed,
    Map<String, String>? uncertain,
    List<String>? pendingQuestions,
    List<String>? skillsInvoked,
    this.currentSeverity = 'green',
  })  : confirmed = confirmed ?? {},
        uncertain = uncertain ?? {},
        pendingQuestions = pendingQuestions ?? [],
        skillsInvoked = skillsInvoked ?? [];

  /// Update running severity -- only escalates, never de-escalates.
  void updateSeverity(String severity) {
    const order = {'green': 0, 'yellow': 1, 'red': 2};
    if ((order[severity] ?? 0) > (order[currentSeverity] ?? 0)) {
      currentSeverity = severity;
    }
  }

  /// Reset per-step tracking when advancing to a new IMCI step.
  void resetForStep() {
    skillsInvoked.clear();
    pendingQuestions.clear();
  }

  /// Record that a skill has been executed this step.
  void markSkillInvoked(String skillName) {
    if (!skillsInvoked.contains(skillName)) {
      skillsInvoked.add(skillName);
    }
  }

  /// Confirm a clinical finding.
  void confirmFinding(String key, dynamic value) {
    confirmed[key] = value;
    uncertain.remove(key);
  }

  /// Mark a finding as uncertain with a reason.
  void markUncertain(String key, String reason) {
    if (!confirmed.containsKey(key)) {
      uncertain[key] = reason;
    }
  }
}

// ============================================================================
// Skill Registry
// ============================================================================

/// Central registry for all clinical skills.
///
/// Skills are registered at import time via [registerAllSkills].
/// The registry provides lookup by name, by IMCI step, and formatted
/// tool descriptions for injecting into Gemma 4's system prompt.
class SkillRegistry {
  static final Map<String, Skill> _skills = {};

  /// Register a skill. Returns the skill for chaining.
  static Skill register(Skill skill) {
    _skills[skill.name] = skill;
    return skill;
  }

  /// Get a skill by name. Throws [StateError] if not found.
  static Skill get(String name) {
    final skill = _skills[name];
    if (skill == null) {
      throw StateError('Skill not found: $name');
    }
    return skill;
  }

  /// Get all skills for a given IMCI step.
  static List<Skill> forStep(String step) {
    return _skills.values.where((s) => s.imciStep == step).toList();
  }

  /// Get all registered skills.
  static List<Skill> listAll() {
    return _skills.values.toList();
  }

  /// Get skills that require media input for a given step.
  static List<Skill> mediaSkillsForStep(String step) {
    return forStep(step).where((s) => s.requiresMedia).toList();
  }

  /// Format skills as tool descriptions for Gemma 4 context.
  ///
  /// Produces a structured text block that tells Gemma 4 what tools
  /// are available for the current IMCI step. Also includes universal
  /// ("any") skills.
  static String asToolDescriptions(String step) {
    final skills = forStep(step);
    // Also include universal skills
    for (final s in _skills.values) {
      if (s.imciStep == 'any' && !skills.contains(s)) {
        skills.add(s);
      }
    }

    if (skills.isEmpty) {
      return 'No specialized skills available for this step.';
    }

    final lines = <String>['Available clinical skills for this step:'];
    for (final s in skills) {
      final params = s.parameters.entries
          .map((e) => '${e.key}: ${e.value}')
          .join(', ');
      final returns = s.returns.entries
          .map((e) => '${e.key}: ${e.value}')
          .join(', ');
      final mediaNote = s.requiresMedia ? ' [Requires: ${s.inputType}]' : '';
      lines.add('  - ${s.name}: ${s.description}$mediaNote');
      if (params.isNotEmpty) lines.add('    Input: $params');
      if (returns.isNotEmpty) lines.add('    Output: $returns');
    }

    return lines.join('\n');
  }
}

// ============================================================================
// Skill Definitions -- All 12 Clinical Skills
// ============================================================================

/// Call this once at app startup to register all skills.
/// Safe to call multiple times (idempotent -- overwrites same keys).
void registerAllSkills() {
  // === DANGER SIGNS SKILLS ===

  SkillRegistry.register(const Skill(
    name: 'assess_alertness',
    description:
        'Analyze a photo of the child to assess alertness level '
        '(alert, lethargic, or unconscious)',
    imciStep: 'danger_signs',
    inputType: 'image',
    parameters: {'image': 'Photo of the child\'s face and upper body'},
    returns: {
      'alert': 'Child is awake and responsive (bool)',
      'lethargic': 'Child is abnormally sleepy, difficult to wake (bool)',
      'unconscious': 'Child cannot be woken (bool)',
    },
    requiresMedia: true,
    mediaPrompt:
        'Can you hold the phone so I can see your child? '
        'I want to check how alert they are.',
  ));

  SkillRegistry.register(const Skill(
    name: 'assess_skin_color',
    description:
        'Analyze skin color from a photo to detect jaundice, cyanosis, '
        'or pallor',
    imciStep: 'danger_signs',
    inputType: 'image',
    parameters: {'image': 'Photo showing the child\'s skin'},
    returns: {
      'jaundice': 'Yellowish skin/eyes suggesting liver issues (bool)',
      'cyanosis': 'Bluish skin suggesting low oxygen (bool)',
      'pallor': 'Pale skin suggesting anemia (bool)',
    },
    requiresMedia: true,
    mediaPrompt:
        'I\'d like to look at your child\'s skin color. '
        'Can you show me their face in good light?',
  ));

  SkillRegistry.register(const Skill(
    name: 'parse_caregiver_response',
    description:
        'Extract clinical facts from the caregiver\'s spoken or typed '
        'response',
    imciStep: 'any',
    inputType: 'text',
    parameters: {
      'text': 'Caregiver\'s response (transcribed speech or typed)',
    },
    returns: {
      'intent':
          'What the caregiver is communicating '
          '(affirmative/negative/informative/uncertain)',
      'entities': 'Clinical entities mentioned (symptoms, duration, severity)',
      'findings': 'Extracted IMCI-relevant findings',
    },
  ));

  // === BREATHING SKILLS ===

  SkillRegistry.register(const Skill(
    name: 'detect_chest_indrawing',
    description:
        'Analyze a chest photo to detect subcostal or intercostal chest '
        'indrawing (WHO danger sign)',
    imciStep: 'breathing',
    inputType: 'image',
    parameters: {'image': 'Photo of the child\'s chest area'},
    returns: {
      'indrawing_detected':
          'Lower chest pulls inward when breathing (bool)',
      'description': 'What was observed in the image',
    },
    requiresMedia: true,
    mediaPrompt:
        'Can you take a photo of your child\'s chest area? '
        'I want to check how they are breathing.',
  ));

  SkillRegistry.register(const Skill(
    name: 'count_breathing_rate',
    description:
        'Count breathing rate from a 15-second video of the child\'s chest',
    imciStep: 'breathing',
    inputType: 'video',
    parameters: {'video': '15-second video of chest wall movement'},
    returns: {
      'rate_per_minute': 'Breaths per minute (int)',
      'is_fast': 'Whether rate exceeds WHO threshold for age (bool)',
    },
    requiresMedia: true,
    mediaPrompt:
        'Can you record a short video of your child\'s chest for about '
        '15 seconds? I need to count their breathing.',
  ));

  SkillRegistry.register(const Skill(
    name: 'classify_breath_sounds',
    description:
        'Classify breath sounds from audio or spectrogram to detect '
        'wheeze, stridor, or grunting',
    imciStep: 'breathing',
    inputType: 'audio',
    parameters: {'audio': 'Recording of the child\'s breathing sounds'},
    returns: {
      'wheeze': 'Whistling sound during breathing (bool)',
      'stridor': 'Harsh high-pitched sound when calm (bool)',
      'grunting': 'Short grunting noise with each breath (bool)',
      'crackles': 'Crackling/bubbling sound (bool)',
    },
    requiresMedia: true,
    mediaPrompt:
        'Can you hold the phone near your child\'s chest so I can '
        'listen to their breathing?',
  ));

  // === DIARRHEA SKILLS ===

  SkillRegistry.register(const Skill(
    name: 'assess_dehydration_signs',
    description:
        'Analyze a photo of the child\'s face to detect dehydration '
        'signs (sunken eyes, dry appearance)',
    imciStep: 'diarrhea',
    inputType: 'image',
    parameters: {'image': 'Photo of the child\'s face'},
    returns: {
      'sunken_eyes':
          'Eyes appear sunken or deeper than normal (bool)',
      'dry_appearance': 'Child\'s skin or mouth appears dry (bool)',
      'description': 'What was observed',
    },
    requiresMedia: true,
    mediaPrompt:
        'Can you take a close photo of your child\'s face? '
        'I want to check for signs of dehydration.',
  ));

  // === NUTRITION SKILLS ===

  SkillRegistry.register(const Skill(
    name: 'assess_wasting',
    description:
        'Analyze a photo to detect visible severe wasting '
        '(very thin, ribs/bones showing)',
    imciStep: 'nutrition',
    inputType: 'image',
    parameters: {'image': 'Photo showing the child\'s body'},
    returns: {
      'visible_wasting': 'Severe visible wasting observed (bool)',
      'description': 'What was observed',
    },
    requiresMedia: true,
    mediaPrompt:
        'Can you take a photo showing your child\'s body? '
        'I want to check their nutrition.',
  ));

  SkillRegistry.register(const Skill(
    name: 'detect_edema',
    description:
        'Analyze a photo to detect bilateral pitting edema of the feet',
    imciStep: 'nutrition',
    inputType: 'image',
    parameters: {'image': 'Photo of the child\'s feet'},
    returns: {
      'edema_detected': 'Swelling in both feet (bool)',
      'description': 'What was observed',
    },
    requiresMedia: true,
    mediaPrompt:
        'Can you show me your child\'s feet? '
        'I want to check for any swelling.',
  ));

  // === CLINICAL SKILLS (deterministic -- run by code, not LLM) ===

  SkillRegistry.register(const Skill(
    name: 'classify_imci_step',
    description:
        'Run WHO IMCI deterministic classification for the completed '
        'assessment step',
    imciStep: 'any',
    inputType: 'findings',
    parameters: {
      'step': 'IMCI step name',
      'findings': 'Collected clinical findings',
    },
    returns: {
      'classification': 'WHO IMCI classification label',
      'severity': 'RED, YELLOW, or GREEN',
      'reasoning':
          'Why this classification was assigned with WHO page reference',
    },
  ));

  SkillRegistry.register(const Skill(
    name: 'generate_treatment',
    description:
        'Generate a step-by-step treatment plan based on WHO IMCI '
        'classifications',
    imciStep: 'treatment',
    inputType: 'findings',
    parameters: {
      'classifications': 'All IMCI classifications from assessment',
      'age_months': 'Child\'s age in months',
      'language': 'Language for instructions',
    },
    returns: {
      'treatment_plan': 'Step-by-step caregiver instructions',
      'urgency': 'How urgently to seek care',
      'follow_up': 'When to return for checkup',
    },
  ));

  SkillRegistry.register(const Skill(
    name: 'speak_to_caregiver',
    description:
        'Generate an empathetic, culturally sensitive voice response '
        'for the caregiver',
    imciStep: 'any',
    inputType: 'text',
    parameters: {
      'context': 'Current assessment context and what to communicate',
    },
    returns: {'response': 'Natural language response for the caregiver'},
  ));
}
