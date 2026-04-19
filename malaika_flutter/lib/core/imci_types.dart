/// Shared type definitions for Malaika IMCI protocol.
///
/// Direct port of malaika/types.py — all enums and classification types.
/// This file has ZERO dependencies on other Malaika modules.
library;

// ---------------------------------------------------------------------------
// IMCI State Machine
// ---------------------------------------------------------------------------

/// States in the WHO IMCI assessment flow. Order is the mandatory protocol sequence.
enum IMCIState {
  dangerSigns,
  breathing,
  diarrhea,
  fever,
  nutrition,
  heartMems,
  classify,
  treat,
  complete,
}

// ---------------------------------------------------------------------------
// Severity & Classification
// ---------------------------------------------------------------------------

/// WHO IMCI severity classification — the traffic light system.
enum Severity {
  green('green'),   // Home care
  yellow('yellow'), // Specific treatment / referral within 24h
  red('red');       // Urgent referral — go NOW

  const Severity(this.value);
  final String value;
}

/// How urgently the child needs a health facility.
enum ReferralUrgency {
  none('none'),           // Green — treat at home
  within24h('24h'),       // Yellow — see a health worker within a day
  immediate('immediate'); // Red — transport to facility NOW

  const ReferralUrgency(this.value);
  final String value;
}

/// Individual IMCI classifications that can be assigned.
enum ClassificationType {
  // Danger signs
  urgentReferral('urgent_referral'),

  // Breathing / Pneumonia
  severePneumonia('severe_pneumonia'),
  pneumonia('pneumonia'),
  noPneumoniaCoughOrCold('no_pneumonia_cough_or_cold'),

  // Diarrhea
  noDiarrhea('no_diarrhea'),
  severeDehydration('severe_dehydration'),
  someDehydration('some_dehydration'),
  noDehydration('no_dehydration'),
  severePersistentDiarrhea('severe_persistent_diarrhea'),
  persistentDiarrhea('persistent_diarrhea'),
  dysentery('dysentery'),

  // Fever
  noFever('no_fever'),
  verySevereFebrileDisease('very_severe_febrile_disease'),
  malaria('malaria'),
  feverNoMalaria('fever_no_malaria'),
  measlesWithComplications('measles_with_complications'),
  measles('measles'),

  // Nutrition
  severeMalnutrition('severe_malnutrition'),
  moderateMalnutrition('moderate_malnutrition'),
  noMalnutrition('no_malnutrition'),

  // Ear
  mastoiditis('mastoiditis'),
  acuteEarInfection('acute_ear_infection'),
  chronicEarInfection('chronic_ear_infection'),
  noEarInfection('no_ear_infection'),

  // Jaundice (neonatal extension)
  severeJaundice('severe_jaundice'),
  jaundice('jaundice'),

  // Heart (MEMS — pluggable)
  heartAbnormality('heart_abnormality'),
  heartNormal('heart_normal'),

  // Healthy
  healthy('healthy');

  const ClassificationType(this.value);
  final String value;
}

/// Status of a single clinical finding from AI perception.
enum FindingStatus {
  detected('detected'),
  notDetected('not_detected'),
  uncertain('uncertain'),
  notAssessed('not_assessed');

  const FindingStatus(this.value);
  final String value;
}
