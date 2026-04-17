/// WHO IMCI Protocol — deterministic classification logic.
///
/// THIS IS THE MEDICAL SAFETY BOUNDARY.
///
/// Every function in this module is pure: same input → same output, always.
/// Every threshold is from the WHO IMCI Chart Booklet with page citations.
/// This module MUST NOT import inference code or call any AI.
///
/// Direct port of malaika/imci_protocol.py.
///
/// Reference: WHO IMCI Chart Booklet (2014 revision, reaffirmed 2023)
/// https://www.who.int/publications/i/item/9789241506823
library;

import 'package:flutter/foundation.dart';
import 'imci_types.dart';

// ============================================================================
// WHO THRESHOLDS — Constants
// ============================================================================

/// Breathing rate thresholds (breaths per minute)
/// Source: IMCI Chart Booklet, p.5
const int fastBreathingThreshold2To11Months = 50; // >= 50 = fast breathing
const int fastBreathingThreshold12To59Months = 40; // >= 40 = fast breathing

/// Diarrhea duration thresholds (days) — Source: IMCI Chart Booklet, p.9
const int persistentDiarrheaThresholdDays = 14; // >= 14 days = persistent

/// Fever duration thresholds (days) — Source: IMCI Chart Booklet, p.11
const int feverDurationConcernDays = 7; // >= 7 days = prolonged fever

/// MUAC thresholds (mm) — Source: IMCI Chart Booklet, p.14
const int muacSevereThresholdMm = 115;   // < 115mm = severe acute malnutrition
const int muacModerateThresholdMm = 125; // 115-124mm = moderate acute malnutrition

/// Dehydration classification requires this many signs — Source: IMCI Chart Booklet, p.8
const int severeDehydrationMinSigns = 2;
const int someDehydrationMinSigns = 2;

/// Heart rate thresholds (BPM) — pediatric — Source: PALS guidelines
const int heartRateTachycardiaInfant = 160; // > 160 in <1yr
const int heartRateTachycardiaChild = 140;  // > 140 in 1-5yr
const int heartRateBradycardia = 60;        // < 60 at any age

// ============================================================================
// Classification Result
// ============================================================================

/// Result of classifying one IMCI domain.
@immutable
class DomainClassification {
  final ClassificationType classification;
  final Severity severity;
  final ReferralUrgency referral;
  final String reasoning;

  const DomainClassification({
    required this.classification,
    required this.severity,
    required this.referral,
    required this.reasoning,
  });
}

/// Final classification combining all IMCI domains.
class AggregateClassification {
  final List<DomainClassification> classifications;

  AggregateClassification({List<DomainClassification>? classifications})
      : classifications = classifications ?? [];

  /// Worst severity across all domains. RED > YELLOW > GREEN.
  Severity get severity {
    if (classifications.isEmpty) return Severity.green;
    const order = {Severity.red: 2, Severity.yellow: 1, Severity.green: 0};
    return classifications
        .reduce((a, b) => order[a.severity]! > order[b.severity]! ? a : b)
        .severity;
  }

  /// Most urgent referral across all domains.
  ReferralUrgency get referral {
    if (classifications.isEmpty) return ReferralUrgency.none;
    const order = {
      ReferralUrgency.immediate: 2,
      ReferralUrgency.within24h: 1,
      ReferralUrgency.none: 0,
    };
    return classifications
        .reduce((a, b) => order[a.referral]! > order[b.referral]! ? a : b)
        .referral;
  }

  /// All classification types assigned across domains.
  List<ClassificationType> get allClassificationTypes =>
      classifications.map((c) => c.classification).toList();
}

// ============================================================================
// DANGER SIGNS — IMCI Chart Booklet p.2
// ============================================================================

/// Classify general danger signs per WHO IMCI.
///
/// ANY single danger sign present → URGENT REFERRAL (RED).
/// No danger signs → returns null (no classification for this domain).
///
/// Source: IMCI Chart Booklet, p.2 — "Check for general danger signs"
DomainClassification? classifyDangerSigns({
  bool lethargic = false,
  bool unconscious = false,
  bool unableToDrink = false,
  bool unableToBreastfeed = false,
  bool convulsions = false,
  bool vomitsEverything = false,
}) {
  final signsPresent = <String>[];
  if (lethargic) signsPresent.add('lethargic');
  if (unconscious) signsPresent.add('unconscious');
  if (unableToDrink) signsPresent.add('unable to drink');
  if (unableToBreastfeed) signsPresent.add('unable to breastfeed');
  if (convulsions) signsPresent.add('convulsions');
  if (vomitsEverything) signsPresent.add('vomits everything');

  if (signsPresent.isEmpty) return null;

  return DomainClassification(
    classification: ClassificationType.urgentReferral,
    severity: Severity.red,
    referral: ReferralUrgency.immediate,
    reasoning:
        'General danger sign(s): ${signsPresent.join(', ')}. '
        'WHO IMCI p.2: Any danger sign → urgent referral.',
  );
}

// ============================================================================
// BREATHING / PNEUMONIA — IMCI Chart Booklet p.5
// ============================================================================

/// Get fast breathing threshold for age group.
///
/// Source: IMCI Chart Booklet p.5
/// - 2 to 11 months: >= 50 breaths/min
/// - 12 to 59 months: >= 40 breaths/min
int _getBreathingThreshold(int ageMonths) {
  if (2 <= ageMonths && ageMonths <= 11) {
    return fastBreathingThreshold2To11Months;
  }
  return fastBreathingThreshold12To59Months;
}

/// Check if breathing rate exceeds WHO IMCI threshold for age group.
bool isFastBreathing(int rate, int ageMonths) {
  if (ageMonths < 2 || ageMonths > 59) {
    throw ArgumentError('ageMonths must be between 2 and 59, got $ageMonths');
  }
  return rate >= _getBreathingThreshold(ageMonths);
}

/// Classify cough/breathing per WHO IMCI.
///
/// Classification hierarchy (worst first):
/// 1. Chest indrawing OR stridor at rest → SEVERE PNEUMONIA (RED)
/// 2. Fast breathing for age → PNEUMONIA (YELLOW)
/// 3. Cough but no fast breathing → NO PNEUMONIA: COUGH OR COLD (GREEN)
///
/// Source: IMCI Chart Booklet, p.5
DomainClassification classifyBreathing({
  required int ageMonths,
  bool hasCough = false,
  int? breathingRate,
  bool hasIndrawing = false,
  bool hasStridor = false,
  bool hasWheeze = false,
}) {
  if (ageMonths < 2 || ageMonths > 59) {
    throw ArgumentError(
      'ageMonths must be between 2 and 59 for IMCI, got $ageMonths',
    );
  }

  // SEVERE PNEUMONIA: chest indrawing or stridor at rest
  // Source: IMCI Chart Booklet p.5, pink row
  if (hasIndrawing || hasStridor) {
    final signs = <String>[];
    if (hasIndrawing) signs.add('chest indrawing');
    if (hasStridor) signs.add('stridor at rest');
    return DomainClassification(
      classification: ClassificationType.severePneumonia,
      severity: Severity.red,
      referral: ReferralUrgency.immediate,
      reasoning: 'Severe pneumonia: ${signs.join(', ')}. WHO IMCI p.5.',
    );
  }

  // PNEUMONIA: fast breathing for age
  // Source: IMCI Chart Booklet p.5, yellow row
  if (breathingRate != null) {
    final threshold = _getBreathingThreshold(ageMonths);
    if (breathingRate >= threshold) {
      return DomainClassification(
        classification: ClassificationType.pneumonia,
        severity: Severity.yellow,
        referral: ReferralUrgency.within24h,
        reasoning:
            'Pneumonia: breathing rate $breathingRate/min '
            '>= threshold $threshold/min for age ${ageMonths}mo. WHO IMCI p.5.',
      );
    }
  }

  // NO PNEUMONIA: cough or cold
  // Source: IMCI Chart Booklet p.5, green row
  return DomainClassification(
    classification: ClassificationType.noPneumoniaCoughOrCold,
    severity: Severity.green,
    referral: ReferralUrgency.none,
    reasoning:
        'No pneumonia: ${hasCough ? 'cough present, ' : ''}'
        'no fast breathing, no indrawing. WHO IMCI p.5.',
  );
}

// ============================================================================
// DIARRHEA / DEHYDRATION — IMCI Chart Booklet p.8-9
// ============================================================================

/// Classify diarrhea and dehydration per WHO IMCI.
///
/// Returns null if no diarrhea. Otherwise classifies dehydration level,
/// persistent diarrhea, or dysentery.
///
/// Source: IMCI Chart Booklet, p.8-9
DomainClassification? classifyDiarrhea({
  required bool hasDiarrhea,
  int durationDays = 0,
  bool bloodInStool = false,
  bool sunkenEyes = false,
  bool skinPinchSlow = false,
  bool skinPinchVerySlow = false,
  bool unableToDrink = false,
  bool drinksEagerly = false,
  bool restlessIrritable = false,
  bool lethargic = false,
}) {
  if (!hasDiarrhea) return null;

  // Count severe dehydration signs
  // Source: IMCI Chart Booklet p.8, pink row
  final severeSignCount = [
    lethargic,
    sunkenEyes,
    unableToDrink,
    skinPinchVerySlow,
  ].where((s) => s).length;

  if (severeSignCount >= severeDehydrationMinSigns) {
    return DomainClassification(
      classification: ClassificationType.severeDehydration,
      severity: Severity.red,
      referral: ReferralUrgency.immediate,
      reasoning:
          'Severe dehydration: $severeSignCount signs present '
          '(>=$severeDehydrationMinSigns required). WHO IMCI p.8.',
    );
  }

  // Count some dehydration signs
  // Source: IMCI Chart Booklet p.8, yellow row
  final someSignCount = [
    restlessIrritable,
    sunkenEyes,
    drinksEagerly,
    skinPinchSlow,
  ].where((s) => s).length;

  if (someSignCount >= someDehydrationMinSigns) {
    return DomainClassification(
      classification: ClassificationType.someDehydration,
      severity: Severity.yellow,
      referral: ReferralUrgency.within24h,
      reasoning:
          'Some dehydration: $someSignCount signs present '
          '(>=$someDehydrationMinSigns required). WHO IMCI p.8.',
    );
  }

  // Persistent diarrhea (>=14 days) — Source: IMCI Chart Booklet p.9
  if (durationDays >= persistentDiarrheaThresholdDays) {
    if (severeSignCount > 0 || someSignCount > 0) {
      return DomainClassification(
        classification: ClassificationType.severePersistentDiarrhea,
        severity: Severity.red,
        referral: ReferralUrgency.immediate,
        reasoning:
            'Severe persistent diarrhea: $durationDays days '
            'with dehydration signs. WHO IMCI p.9.',
      );
    }
    return DomainClassification(
      classification: ClassificationType.persistentDiarrhea,
      severity: Severity.yellow,
      referral: ReferralUrgency.within24h,
      reasoning:
          'Persistent diarrhea: $durationDays days '
          '(>=$persistentDiarrheaThresholdDays). WHO IMCI p.9.',
    );
  }

  // Dysentery (blood in stool) — Source: IMCI Chart Booklet p.9
  if (bloodInStool) {
    return const DomainClassification(
      classification: ClassificationType.dysentery,
      severity: Severity.yellow,
      referral: ReferralUrgency.within24h,
      reasoning: 'Dysentery: blood in stool. WHO IMCI p.9.',
    );
  }

  // No dehydration — Source: IMCI Chart Booklet p.8, green row
  return const DomainClassification(
    classification: ClassificationType.noDehydration,
    severity: Severity.green,
    referral: ReferralUrgency.none,
    reasoning:
        'No dehydration: insufficient dehydration signs. WHO IMCI p.8.',
  );
}

// ============================================================================
// FEVER — IMCI Chart Booklet p.11
// ============================================================================

/// Classify fever per WHO IMCI.
///
/// Source: IMCI Chart Booklet, p.11 — "Does the child have fever?"
DomainClassification? classifyFever({
  required bool hasFever,
  int durationDays = 0,
  bool stiffNeck = false,
  bool malariaRisk = false,
  bool measlesRecent = false,
  bool measlesComplications = false,
}) {
  if (!hasFever) return null;

  // VERY SEVERE FEBRILE DISEASE — stiff neck = meningitis risk
  // Source: IMCI Chart Booklet p.11, pink row
  if (stiffNeck) {
    return const DomainClassification(
      classification: ClassificationType.verySevereFebrileDisease,
      severity: Severity.red,
      referral: ReferralUrgency.immediate,
      reasoning:
          'Very severe febrile disease: stiff neck present. WHO IMCI p.11.',
    );
  }

  // MALARIA (in malaria-risk area)
  // Source: IMCI Chart Booklet p.11, yellow row
  if (malariaRisk) {
    return DomainClassification(
      classification: ClassificationType.malaria,
      severity: Severity.yellow,
      referral: ReferralUrgency.within24h,
      reasoning:
          'Malaria: fever $durationDays days in malaria-risk area. '
          'WHO IMCI p.11.',
    );
  }

  // MEASLES WITH COMPLICATIONS — Source: IMCI Chart Booklet p.12
  if (measlesRecent && measlesComplications) {
    return const DomainClassification(
      classification: ClassificationType.measlesWithComplications,
      severity: Severity.yellow,
      referral: ReferralUrgency.within24h,
      reasoning: 'Measles with complications. WHO IMCI p.12.',
    );
  }

  // MEASLES (without complications)
  if (measlesRecent) {
    return const DomainClassification(
      classification: ClassificationType.measles,
      severity: Severity.yellow,
      referral: ReferralUrgency.within24h,
      reasoning: 'Measles (recent, without complications). WHO IMCI p.12.',
    );
  }

  // FEVER — no specific cause identified
  // Source: IMCI Chart Booklet p.11, yellow/green row
  return DomainClassification(
    classification: ClassificationType.feverNoMalaria,
    severity: Severity.yellow,
    referral: ReferralUrgency.within24h,
    reasoning:
        'Fever $durationDays days, no malaria risk, '
        'no stiff neck. WHO IMCI p.11.',
  );
}

// ============================================================================
// NUTRITION — IMCI Chart Booklet p.14
// ============================================================================

/// Classify nutritional status per WHO IMCI.
///
/// Source: IMCI Chart Booklet, p.14 — "Check for malnutrition"
DomainClassification classifyNutrition({
  bool visibleWasting = false,
  bool edema = false,
  int? muacMm,
}) {
  // SEVERE MALNUTRITION
  // Source: IMCI Chart Booklet p.14, pink row
  final isSevere = visibleWasting ||
      edema ||
      (muacMm != null && muacMm < muacSevereThresholdMm);

  if (isSevere) {
    final reasons = <String>[];
    if (visibleWasting) reasons.add('visible severe wasting');
    if (edema) reasons.add('edema both feet');
    if (muacMm != null && muacMm < muacSevereThresholdMm) {
      reasons.add('MUAC ${muacMm}mm < ${muacSevereThresholdMm}mm');
    }
    return DomainClassification(
      classification: ClassificationType.severeMalnutrition,
      severity: Severity.red,
      referral: ReferralUrgency.immediate,
      reasoning:
          'Severe malnutrition: ${reasons.join(', ')}. WHO IMCI p.14.',
    );
  }

  // MODERATE MALNUTRITION — MUAC 115-124mm
  // Source: IMCI Chart Booklet p.14, yellow row
  if (muacMm != null && muacMm < muacModerateThresholdMm) {
    return DomainClassification(
      classification: ClassificationType.moderateMalnutrition,
      severity: Severity.yellow,
      referral: ReferralUrgency.within24h,
      reasoning:
          'Moderate malnutrition: MUAC ${muacMm}mm '
          '(threshold: ${muacModerateThresholdMm}mm). WHO IMCI p.14.',
    );
  }

  // NO MALNUTRITION
  return DomainClassification(
    classification: ClassificationType.noMalnutrition,
    severity: Severity.green,
    referral: ReferralUrgency.none,
    reasoning:
        'No malnutrition: no wasting, no edema'
        '${muacMm != null ? ', MUAC ${muacMm}mm' : ''}. WHO IMCI p.14.',
  );
}

// ============================================================================
// HEART (MEMS — Pluggable) — Not standard IMCI
// ============================================================================

/// Classify heart assessment (MEMS module — non-standard IMCI extension).
///
/// Returns null if no data provided.
DomainClassification? classifyHeart({
  required int ageMonths,
  int? estimatedBpm,
  bool abnormalSounds = false,
}) {
  if (estimatedBpm == null && !abnormalSounds) return null;

  if (estimatedBpm != null) {
    final threshold = ageMonths < 12
        ? heartRateTachycardiaInfant
        : heartRateTachycardiaChild;

    if (estimatedBpm > threshold || estimatedBpm < heartRateBradycardia) {
      return DomainClassification(
        classification: ClassificationType.heartAbnormality,
        severity: Severity.yellow,
        referral: ReferralUrgency.within24h,
        reasoning:
            'Heart rate $estimatedBpm BPM outside normal range '
            'for age ${ageMonths}mo. PALS guidelines.',
      );
    }
  }

  if (abnormalSounds) {
    return const DomainClassification(
      classification: ClassificationType.heartAbnormality,
      severity: Severity.yellow,
      referral: ReferralUrgency.within24h,
      reasoning: 'Abnormal heart sounds detected. Refer for evaluation.',
    );
  }

  return DomainClassification(
    classification: ClassificationType.heartNormal,
    severity: Severity.green,
    referral: ReferralUrgency.none,
    reasoning:
        'Heart rate $estimatedBpm BPM, normal for age ${ageMonths}mo.',
  );
}

// ============================================================================
// AGGREGATE CLASSIFICATION
// ============================================================================

/// Run full IMCI classification across all domains.
///
/// Takes structured findings from each domain and produces
/// an aggregate classification with worst-severity determination.
AggregateClassification classifyAssessment({
  required int ageMonths,
  Map<String, dynamic>? dangerSigns,
  Map<String, dynamic>? breathing,
  Map<String, dynamic>? diarrhea,
  Map<String, dynamic>? fever,
  Map<String, dynamic>? nutrition,
  Map<String, dynamic>? heart,
}) {
  final result = AggregateClassification();

  // 1. Danger signs (always first)
  if (dangerSigns != null) {
    final dangerResult = classifyDangerSigns(
      lethargic: dangerSigns['lethargic'] as bool? ?? false,
      unconscious: dangerSigns['unconscious'] as bool? ?? false,
      unableToDrink: dangerSigns['unable_to_drink'] as bool? ?? false,
      unableToBreastfeed: dangerSigns['unable_to_breastfeed'] as bool? ?? false,
      convulsions: dangerSigns['convulsions'] as bool? ?? false,
      vomitsEverything: dangerSigns['vomits_everything'] as bool? ?? false,
    );
    if (dangerResult != null) result.classifications.add(dangerResult);
  }

  // 2. Breathing
  if (breathing != null) {
    final breathingResult = classifyBreathing(
      ageMonths: ageMonths,
      hasCough: breathing['has_cough'] as bool? ?? false,
      breathingRate: breathing['breathing_rate'] as int?,
      hasIndrawing: breathing['has_indrawing'] as bool? ?? false,
      hasStridor: breathing['has_stridor'] as bool? ?? false,
      hasWheeze: breathing['has_wheeze'] as bool? ?? false,
    );
    result.classifications.add(breathingResult);
  }

  // 3. Diarrhea
  if (diarrhea != null) {
    final diarrheaResult = classifyDiarrhea(
      hasDiarrhea: diarrhea['has_diarrhea'] as bool? ?? false,
      durationDays: diarrhea['duration_days'] as int? ?? 0,
      bloodInStool: diarrhea['blood_in_stool'] as bool? ?? false,
      sunkenEyes: diarrhea['sunken_eyes'] as bool? ?? false,
      skinPinchSlow: diarrhea['skin_pinch_slow'] as bool? ?? false,
      skinPinchVerySlow: diarrhea['skin_pinch_very_slow'] as bool? ?? false,
      unableToDrink: diarrhea['unable_to_drink'] as bool? ?? false,
      drinksEagerly: diarrhea['drinks_eagerly'] as bool? ?? false,
      restlessIrritable: diarrhea['restless_irritable'] as bool? ?? false,
      lethargic: diarrhea['lethargic'] as bool? ?? false,
    );
    if (diarrheaResult != null) result.classifications.add(diarrheaResult);
  }

  // 4. Fever
  if (fever != null) {
    final feverResult = classifyFever(
      hasFever: fever['has_fever'] as bool? ?? false,
      durationDays: fever['duration_days'] as int? ?? 0,
      stiffNeck: fever['stiff_neck'] as bool? ?? false,
      malariaRisk: fever['malaria_risk'] as bool? ?? false,
      measlesRecent: fever['measles_recent'] as bool? ?? false,
      measlesComplications: fever['measles_complications'] as bool? ?? false,
    );
    if (feverResult != null) result.classifications.add(feverResult);
  }

  // 5. Nutrition
  if (nutrition != null) {
    final nutritionResult = classifyNutrition(
      visibleWasting: nutrition['visible_wasting'] as bool? ?? false,
      edema: nutrition['edema'] as bool? ?? false,
      muacMm: nutrition['muac_mm'] as int?,
    );
    result.classifications.add(nutritionResult);
  }

  // 6. Heart (pluggable)
  if (heart != null) {
    final heartResult = classifyHeart(
      ageMonths: ageMonths,
      estimatedBpm: heart['estimated_bpm'] as int?,
      abnormalSounds: heart['abnormal_sounds'] as bool? ?? false,
    );
    if (heartResult != null) result.classifications.add(heartResult);
  }

  // If no classifications at all → healthy
  if (result.classifications.isEmpty) {
    result.classifications.add(const DomainClassification(
      classification: ClassificationType.healthy,
      severity: Severity.green,
      referral: ReferralUrgency.none,
      reasoning: 'No IMCI classifications triggered. Child appears healthy.',
    ));
  }

  return result;
}
