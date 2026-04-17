/// Tests for WHO IMCI protocol classification logic.
///
/// Target: 100% coverage on imci_protocol.dart.
/// Every threshold boundary, every classification path, every edge case.
///
/// Direct port of tests/test_imci_protocol.py — all 78 tests preserved.
import 'package:flutter_test/flutter_test.dart';
import 'package:malaika_flutter/core/imci_protocol.dart';
import 'package:malaika_flutter/core/imci_types.dart';

void main() {
  // ==========================================================================
  // DANGER SIGNS
  // ==========================================================================

  group('classifyDangerSigns — IMCI Chart Booklet p.2', () {
    test('no danger signs returns null', () {
      final result = classifyDangerSigns();
      expect(result, isNull);
    });

    test('lethargic triggers urgent', () {
      final result = classifyDangerSigns(lethargic: true);
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.urgentReferral);
      expect(result.severity, Severity.red);
      expect(result.referral, ReferralUrgency.immediate);
    });

    test('unconscious triggers urgent', () {
      final result = classifyDangerSigns(unconscious: true);
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.urgentReferral);
    });

    test('unable to drink triggers urgent', () {
      final result = classifyDangerSigns(unableToDrink: true);
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.urgentReferral);
    });

    test('unable to breastfeed triggers urgent', () {
      final result = classifyDangerSigns(unableToBreastfeed: true);
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.urgentReferral);
    });

    test('convulsions triggers urgent', () {
      final result = classifyDangerSigns(convulsions: true);
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.urgentReferral);
    });

    test('vomits everything triggers urgent', () {
      final result = classifyDangerSigns(vomitsEverything: true);
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.urgentReferral);
    });

    test('multiple signs still urgent', () {
      final result =
          classifyDangerSigns(lethargic: true, convulsions: true);
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.urgentReferral);
      expect(result.reasoning, contains('lethargic'));
      expect(result.reasoning, contains('convulsions'));
    });

    test('all false returns null', () {
      final result = classifyDangerSigns(
        lethargic: false,
        unconscious: false,
        unableToDrink: false,
        unableToBreastfeed: false,
        convulsions: false,
        vomitsEverything: false,
      );
      expect(result, isNull);
    });
  });

  // ==========================================================================
  // BREATHING / PNEUMONIA
  // ==========================================================================

  group('classifyBreathing — IMCI Chart Booklet p.5', () {
    // --- Severe pneumonia (RED) ---

    test('chest indrawing is severe', () {
      final result =
          classifyBreathing(ageMonths: 6, hasIndrawing: true);
      expect(result.classification, ClassificationType.severePneumonia);
      expect(result.severity, Severity.red);
    });

    test('stridor is severe', () {
      final result =
          classifyBreathing(ageMonths: 6, hasStridor: true);
      expect(result.classification, ClassificationType.severePneumonia);
    });

    test('indrawing and stridor is severe', () {
      final result = classifyBreathing(
        ageMonths: 6,
        hasIndrawing: true,
        hasStridor: true,
      );
      expect(result.classification, ClassificationType.severePneumonia);
      expect(result.reasoning, contains('chest indrawing'));
      expect(result.reasoning, contains('stridor'));
    });

    // --- Pneumonia (YELLOW) — fast breathing ---

    test('fast breathing infant at threshold (50/min at 6mo)', () {
      final result =
          classifyBreathing(ageMonths: 6, breathingRate: 50);
      expect(result.classification, ClassificationType.pneumonia);
      expect(result.severity, Severity.yellow);
    });

    test('fast breathing infant above threshold', () {
      final result =
          classifyBreathing(ageMonths: 6, breathingRate: 55);
      expect(result.classification, ClassificationType.pneumonia);
    });

    test('fast breathing child at threshold (40/min at 24mo)', () {
      final result =
          classifyBreathing(ageMonths: 24, breathingRate: 40);
      expect(result.classification, ClassificationType.pneumonia);
    });

    test('fast breathing child above threshold', () {
      final result =
          classifyBreathing(ageMonths: 24, breathingRate: 45);
      expect(result.classification, ClassificationType.pneumonia);
    });

    // --- No pneumonia (GREEN) ---

    test('normal breathing infant below threshold (49/min at 6mo)', () {
      final result =
          classifyBreathing(ageMonths: 6, breathingRate: 49);
      expect(
        result.classification,
        ClassificationType.noPneumoniaCoughOrCold,
      );
      expect(result.severity, Severity.green);
    });

    test('normal breathing child below threshold (39/min at 24mo)', () {
      final result =
          classifyBreathing(ageMonths: 24, breathingRate: 39);
      expect(
        result.classification,
        ClassificationType.noPneumoniaCoughOrCold,
      );
    });

    test('no breathing rate measured — green', () {
      final result =
          classifyBreathing(ageMonths: 12, hasCough: true);
      expect(
        result.classification,
        ClassificationType.noPneumoniaCoughOrCold,
      );
    });

    // --- Indrawing overrides fast breathing ---

    test('indrawing overrides rate — severe even with normal rate', () {
      final result = classifyBreathing(
        ageMonths: 6,
        breathingRate: 30,
        hasIndrawing: true,
      );
      expect(result.classification, ClassificationType.severePneumonia);
    });

    // --- Age boundaries ---

    test('age 11 months uses 50 threshold', () {
      final result =
          classifyBreathing(ageMonths: 11, breathingRate: 50);
      expect(result.classification, ClassificationType.pneumonia);
    });

    test('age 12 months uses 40 threshold', () {
      final result =
          classifyBreathing(ageMonths: 12, breathingRate: 40);
      expect(result.classification, ClassificationType.pneumonia);
    });

    test('age 12 months 49/min is pneumonia (49 >= 40)', () {
      final result =
          classifyBreathing(ageMonths: 12, breathingRate: 49);
      expect(result.classification, ClassificationType.pneumonia);
    });

    // --- Invalid age ---

    test('age below 2 raises ArgumentError', () {
      expect(
        () => classifyBreathing(ageMonths: 1, breathingRate: 40),
        throwsArgumentError,
      );
    });

    test('age above 59 raises ArgumentError', () {
      expect(
        () => classifyBreathing(ageMonths: 60, breathingRate: 40),
        throwsArgumentError,
      );
    });
  });

  group('isFastBreathing helper', () {
    test('fast infant', () {
      expect(isFastBreathing(50, 6), isTrue);
    });

    test('normal infant', () {
      expect(isFastBreathing(49, 6), isFalse);
    });

    test('fast child', () {
      expect(isFastBreathing(40, 24), isTrue);
    });

    test('normal child', () {
      expect(isFastBreathing(39, 24), isFalse);
    });

    test('invalid age raises ArgumentError', () {
      expect(() => isFastBreathing(40, 1), throwsArgumentError);
    });
  });

  // ==========================================================================
  // DIARRHEA / DEHYDRATION
  // ==========================================================================

  group('classifyDiarrhea — IMCI Chart Booklet p.8-9', () {
    test('no diarrhea returns null', () {
      expect(classifyDiarrhea(hasDiarrhea: false), isNull);
    });

    // --- Severe dehydration (RED) ---

    test('severe dehydration two signs', () {
      final result = classifyDiarrhea(
        hasDiarrhea: true,
        sunkenEyes: true,
        skinPinchVerySlow: true,
      );
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.severeDehydration,
      );
      expect(result.severity, Severity.red);
    });

    test('severe dehydration lethargic and unable to drink', () {
      final result = classifyDiarrhea(
        hasDiarrhea: true,
        lethargic: true,
        unableToDrink: true,
      );
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.severeDehydration,
      );
    });

    // --- Some dehydration (YELLOW) ---

    test('some dehydration two signs', () {
      final result = classifyDiarrhea(
        hasDiarrhea: true,
        sunkenEyes: true,
        skinPinchSlow: true,
      );
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.someDehydration,
      );
      expect(result.severity, Severity.yellow);
    });

    test('some dehydration restless and thirsty', () {
      final result = classifyDiarrhea(
        hasDiarrhea: true,
        restlessIrritable: true,
        drinksEagerly: true,
      );
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.someDehydration,
      );
    });

    // --- Persistent diarrhea ---

    test('persistent diarrhea 14 days', () {
      final result = classifyDiarrhea(
        hasDiarrhea: true,
        durationDays: 14,
      );
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.persistentDiarrhea,
      );
      expect(result.severity, Severity.yellow);
    });

    test('persistent diarrhea with dehydration is severe', () {
      final result = classifyDiarrhea(
        hasDiarrhea: true,
        durationDays: 16,
        sunkenEyes: true,
      );
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.severePersistentDiarrhea,
      );
      expect(result.severity, Severity.red);
    });

    // --- Dysentery ---

    test('dysentery blood in stool', () {
      final result = classifyDiarrhea(
        hasDiarrhea: true,
        bloodInStool: true,
      );
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.dysentery);
      expect(result.severity, Severity.yellow);
    });

    // --- No dehydration (GREEN) ---

    test('no dehydration', () {
      final result = classifyDiarrhea(
        hasDiarrhea: true,
        durationDays: 2,
      );
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.noDehydration,
      );
      expect(result.severity, Severity.green);
    });

    // --- One sign is not enough ---

    test('one severe sign not enough for severe dehydration', () {
      final result = classifyDiarrhea(
        hasDiarrhea: true,
        sunkenEyes: true,
      );
      expect(result, isNotNull);
      // One sign for severe (sunkenEyes) but also counts as one sign for some.
      // Only 1 sign, not >= 2, so not some dehydration either.
      expect(
        result!.classification,
        isNot(ClassificationType.severeDehydration),
      );
    });
  });

  // ==========================================================================
  // FEVER
  // ==========================================================================

  group('classifyFever — IMCI Chart Booklet p.11', () {
    test('no fever returns null', () {
      expect(classifyFever(hasFever: false), isNull);
    });

    test('very severe stiff neck', () {
      final result = classifyFever(hasFever: true, stiffNeck: true);
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.verySevereFebrileDisease,
      );
      expect(result.severity, Severity.red);
    });

    test('malaria with risk', () {
      final result = classifyFever(
        hasFever: true,
        malariaRisk: true,
        durationDays: 3,
      );
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.malaria);
      expect(result.severity, Severity.yellow);
    });

    test('measles with complications', () {
      final result = classifyFever(
        hasFever: true,
        measlesRecent: true,
        measlesComplications: true,
      );
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.measlesWithComplications,
      );
    });

    test('measles without complications', () {
      final result = classifyFever(
        hasFever: true,
        measlesRecent: true,
      );
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.measles);
    });

    test('fever no malaria risk', () {
      final result = classifyFever(
        hasFever: true,
        durationDays: 2,
      );
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.feverNoMalaria);
    });

    test('stiff neck overrides malaria — very severe even in malaria area',
        () {
      final result = classifyFever(
        hasFever: true,
        stiffNeck: true,
        malariaRisk: true,
      );
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.verySevereFebrileDisease,
      );
    });
  });

  // ==========================================================================
  // NUTRITION
  // ==========================================================================

  group('classifyNutrition — IMCI Chart Booklet p.14', () {
    test('severe visible wasting', () {
      final result = classifyNutrition(visibleWasting: true);
      expect(result.classification, ClassificationType.severeMalnutrition);
      expect(result.severity, Severity.red);
    });

    test('severe edema', () {
      final result = classifyNutrition(edema: true);
      expect(result.classification, ClassificationType.severeMalnutrition);
    });

    test('severe MUAC below 115', () {
      final result = classifyNutrition(muacMm: 110);
      expect(result.classification, ClassificationType.severeMalnutrition);
    });

    test('severe MUAC at 114 (114mm < 115mm threshold)', () {
      final result = classifyNutrition(muacMm: 114);
      expect(result.classification, ClassificationType.severeMalnutrition);
    });

    test('moderate MUAC at 115 (115mm is NOT severe but IS moderate)', () {
      final result = classifyNutrition(muacMm: 115);
      expect(
        result.classification,
        ClassificationType.moderateMalnutrition,
      );
    });

    test('moderate MUAC at 124 (124mm < 125mm)', () {
      final result = classifyNutrition(muacMm: 124);
      expect(
        result.classification,
        ClassificationType.moderateMalnutrition,
      );
    });

    test('normal MUAC at 125 (125mm >= 125mm)', () {
      final result = classifyNutrition(muacMm: 125);
      expect(result.classification, ClassificationType.noMalnutrition);
    });

    test('normal MUAC high', () {
      final result = classifyNutrition(muacMm: 150);
      expect(result.classification, ClassificationType.noMalnutrition);
      expect(result.severity, Severity.green);
    });

    test('normal no MUAC', () {
      final result = classifyNutrition();
      expect(result.classification, ClassificationType.noMalnutrition);
    });

    test('wasting overrides normal MUAC — severe even with 140mm', () {
      final result =
          classifyNutrition(visibleWasting: true, muacMm: 140);
      expect(result.classification, ClassificationType.severeMalnutrition);
    });
  });

  // ==========================================================================
  // HEART (MEMS)
  // ==========================================================================

  group('classifyHeart — pluggable MEMS module', () {
    test('no data returns null', () {
      expect(classifyHeart(ageMonths: 12), isNull);
    });

    test('normal heart rate infant', () {
      final result =
          classifyHeart(ageMonths: 6, estimatedBpm: 130);
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.heartNormal);
    });

    test('tachycardia infant', () {
      final result =
          classifyHeart(ageMonths: 6, estimatedBpm: 165);
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.heartAbnormality,
      );
    });

    test('tachycardia child', () {
      final result =
          classifyHeart(ageMonths: 24, estimatedBpm: 145);
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.heartAbnormality,
      );
    });

    test('bradycardia', () {
      final result =
          classifyHeart(ageMonths: 12, estimatedBpm: 55);
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.heartAbnormality,
      );
    });

    test('abnormal sounds', () {
      final result =
          classifyHeart(ageMonths: 12, abnormalSounds: true);
      expect(result, isNotNull);
      expect(
        result!.classification,
        ClassificationType.heartAbnormality,
      );
    });

    test('normal heart rate child', () {
      final result =
          classifyHeart(ageMonths: 36, estimatedBpm: 100);
      expect(result, isNotNull);
      expect(result!.classification, ClassificationType.heartNormal);
    });
  });

  // ==========================================================================
  // AGGREGATE CLASSIFICATION
  // ==========================================================================

  group('classifyAssessment — full IMCI aggregate classification', () {
    test('healthy child — no findings', () {
      final result = classifyAssessment(ageMonths: 18);
      expect(result.severity, Severity.green);
      expect(
        result.allClassificationTypes,
        contains(ClassificationType.healthy),
      );
    });

    test('single domain pneumonia', () {
      final result = classifyAssessment(
        ageMonths: 6,
        breathing: {'breathing_rate': 55, 'has_cough': true},
      );
      expect(result.severity, Severity.yellow);
      expect(
        result.allClassificationTypes,
        contains(ClassificationType.pneumonia),
      );
    });

    test('danger sign makes red', () {
      final result = classifyAssessment(
        ageMonths: 12,
        dangerSigns: {'lethargic': true},
      );
      expect(result.severity, Severity.red);
      expect(result.referral, ReferralUrgency.immediate);
    });

    test('multi domain worst wins — pneumonia YELLOW + severe malnutrition RED = RED',
        () {
      final result = classifyAssessment(
        ageMonths: 8,
        breathing: {'breathing_rate': 55, 'has_cough': true},
        nutrition: {'visible_wasting': true},
      );
      expect(result.severity, Severity.red);
      expect(
        result.allClassificationTypes,
        contains(ClassificationType.pneumonia),
      );
      expect(
        result.allClassificationTypes,
        contains(ClassificationType.severeMalnutrition),
      );
    });

    test('all domains normal', () {
      final result = classifyAssessment(
        ageMonths: 18,
        dangerSigns: {'lethargic': false, 'convulsions': false},
        breathing: {'breathing_rate': 28, 'has_cough': false},
        diarrhea: {'has_diarrhea': false},
        fever: {'has_fever': false},
        nutrition: {
          'visible_wasting': false,
          'edema': false,
          'muac_mm': 150,
        },
      );
      expect(result.severity, Severity.green);
    });

    test('no diarrhea no fever excluded from classifications', () {
      final result = classifyAssessment(
        ageMonths: 18,
        diarrhea: {'has_diarrhea': false},
        fever: {'has_fever': false},
      );
      // Only healthy classification (no diarrhea/fever classifications added)
      final types = result.allClassificationTypes;
      expect(types, isNot(contains(ClassificationType.noDehydration)));
      expect(types, isNot(contains(ClassificationType.feverNoMalaria)));
    });
  });

  // ==========================================================================
  // GOLDEN SCENARIOS — from evaluation/golden_scenarios.py
  // ==========================================================================

  group('Golden scenarios — expected WHO IMCI classifications', () {
    test('danger lethargic', () {
      final result = classifyAssessment(
        ageMonths: 12,
        dangerSigns: {
          'lethargic': true,
          'unable_to_drink': true,
          'convulsions': false,
        },
      );
      expect(result.severity, Severity.red);
      expect(
        result.allClassificationTypes,
        contains(ClassificationType.urgentReferral),
      );
    });

    test('breathing fast infant', () {
      final result = classifyAssessment(
        ageMonths: 6,
        breathing: {
          'breathing_rate': 55,
          'has_cough': true,
          'has_indrawing': false,
          'has_stridor': false,
          'has_wheeze': false,
        },
      );
      expect(
        result.allClassificationTypes,
        contains(ClassificationType.pneumonia),
      );
    });

    test('breathing severe', () {
      final result = classifyAssessment(
        ageMonths: 10,
        breathing: {
          'breathing_rate': 60,
          'has_cough': true,
          'has_indrawing': true,
          'has_stridor': true,
          'has_wheeze': false,
        },
      );
      expect(
        result.allClassificationTypes,
        contains(ClassificationType.severePneumonia),
      );
      expect(result.severity, Severity.red);
    });

    test('diarrhea severe dehydration', () {
      final result = classifyAssessment(
        ageMonths: 8,
        diarrhea: {
          'has_diarrhea': true,
          'duration_days': 3,
          'blood_in_stool': false,
          'sunken_eyes': true,
          'skin_pinch_very_slow': true,
          'unable_to_drink': true,
        },
      );
      expect(
        result.allClassificationTypes,
        contains(ClassificationType.severeDehydration),
      );
    });

    test('fever very severe', () {
      final result = classifyAssessment(
        ageMonths: 24,
        fever: {
          'has_fever': true,
          'duration_days': 3,
          'stiff_neck': true,
          'malaria_risk': true,
        },
      );
      expect(
        result.allClassificationTypes,
        contains(ClassificationType.verySevereFebrileDisease),
      );
    });

    test('nutrition severe wasting', () {
      final result = classifyAssessment(
        ageMonths: 10,
        nutrition: {
          'visible_wasting': true,
          'edema': false,
          'muac_mm': 110,
        },
      );
      expect(
        result.allClassificationTypes,
        contains(ClassificationType.severeMalnutrition),
      );
    });

    test('healthy child — all domains clear', () {
      final result = classifyAssessment(
        ageMonths: 18,
        dangerSigns: {
          'lethargic': false,
          'unable_to_drink': false,
          'convulsions': false,
        },
        breathing: {
          'breathing_rate': 28,
          'has_cough': false,
          'has_indrawing': false,
          'has_stridor': false,
          'has_wheeze': false,
        },
        diarrhea: {'has_diarrhea': false},
        fever: {'has_fever': false},
        nutrition: {
          'visible_wasting': false,
          'edema': false,
          'muac_mm': 150,
        },
      );
      expect(result.severity, Severity.green);
    });

    test('combined pneumonia dehydration', () {
      final result = classifyAssessment(
        ageMonths: 10,
        breathing: {
          'breathing_rate': 55,
          'has_cough': true,
          'has_indrawing': false,
          'has_stridor': false,
          'has_wheeze': false,
        },
        diarrhea: {
          'has_diarrhea': true,
          'duration_days': 2,
          'blood_in_stool': false,
          'sunken_eyes': true,
          'skin_pinch_slow': true,
          'unable_to_drink': false,
        },
      );
      final types = result.allClassificationTypes;
      expect(types, contains(ClassificationType.pneumonia));
      expect(types, contains(ClassificationType.someDehydration));
      expect(result.severity, Severity.yellow);
    });
  });
}
