/// Tests for WHO IMCI treatment protocol dosing logic.
///
/// Target: every weight-band boundary, every age threshold, every ORS plan.
/// All doses verified against WHO IMCI Chart Booklet (2014, reaffirmed 2023).
import 'package:flutter_test/flutter_test.dart';
import 'package:malaika_flutter/core/treatment_protocol.dart';
import 'package:malaika_flutter/core/imci_protocol.dart';
import 'package:malaika_flutter/core/imci_types.dart';

void main() {
  // ==========================================================================
  // WEIGHT ESTIMATION FALLBACK
  // ==========================================================================

  group('estimateWeightFromAge — WHO growth standards', () {
    test('newborn ~ 3.5 kg', () {
      expect(estimateWeightFromAge(0), 3.5);
    });

    test('6 months ~ 7.5 kg', () {
      expect(estimateWeightFromAge(6), 7.5);
    });

    test('12 months ~ 9.5 kg', () {
      expect(estimateWeightFromAge(12), 9.5);
    });

    test('24 months ~ 12.0 kg', () {
      expect(estimateWeightFromAge(24), 12.0);
    });

    test('48 months ~ 16.0 kg', () {
      expect(estimateWeightFromAge(48), 16.0);
    });

    test('59 months ~ 18.0 kg', () {
      expect(estimateWeightFromAge(59), 18.0);
    });
  });

  // ==========================================================================
  // AMOXICILLIN — IMCI Chart Booklet p.18
  // ==========================================================================

  group('prescribeAmoxicillin — weight-band dosing', () {
    test('3 kg → half tablet twice daily', () {
      final rx = prescribeAmoxicillin(3.0);
      expect(rx, isNotNull);
      expect(rx!.medicineName, 'Amoxicillin');
      expect(rx.doseDescription, contains('half'));
      expect(rx.doseMg, 125.0); // 0.5 × 250
      expect(rx.timesPerDay, 2);
      expect(rx.durationDays, 5);
    });

    test('5.9 kg → still half tablet (boundary)', () {
      final rx = prescribeAmoxicillin(5.9);
      expect(rx, isNotNull);
      expect(rx!.doseMg, 125.0);
    });

    test('6.0 kg → 1 tablet (boundary crossover)', () {
      final rx = prescribeAmoxicillin(6.0);
      expect(rx, isNotNull);
      expect(rx!.doseMg, 250.0);
      expect(rx.doseDescription, contains('1 tablet'));
    });

    test('9.9 kg → 1 tablet', () {
      final rx = prescribeAmoxicillin(9.9);
      expect(rx!.doseMg, 250.0);
    });

    test('10.0 kg → 2 tablets (boundary crossover)', () {
      final rx = prescribeAmoxicillin(10.0);
      expect(rx!.doseMg, 500.0);
      expect(rx.doseDescription, contains('2 tablets'));
    });

    test('13.9 kg → 2 tablets', () {
      final rx = prescribeAmoxicillin(13.9);
      expect(rx!.doseMg, 500.0);
    });

    test('14.0 kg → 3 tablets (boundary crossover)', () {
      final rx = prescribeAmoxicillin(14.0);
      expect(rx!.doseMg, 750.0);
      expect(rx.doseDescription, contains('3 tablets'));
    });

    test('18 kg → 3 tablets', () {
      final rx = prescribeAmoxicillin(18.0);
      expect(rx!.doseMg, 750.0);
    });

    test('preparation includes dissolve instruction', () {
      final rx = prescribeAmoxicillin(8.0);
      expect(rx!.preparation, contains('Dissolve'));
    });

    test('WHO reference cited', () {
      final rx = prescribeAmoxicillin(8.0);
      expect(rx!.whoReference, contains('p.18'));
    });
  });

  // ==========================================================================
  // COTRIMOXAZOLE — IMCI Chart Booklet p.18
  // ==========================================================================

  group('prescribeCotrimoxazole — weight-band dosing', () {
    test('4 kg → quarter tablet', () {
      final rx = prescribeCotrimoxazole(4.0);
      expect(rx, isNotNull);
      expect(rx!.doseDescription, contains('quarter'));
      expect(rx.timesPerDay, 2);
      expect(rx.durationDays, 5);
    });

    test('8 kg → half tablet', () {
      final rx = prescribeCotrimoxazole(8.0);
      expect(rx!.doseDescription, contains('half'));
    });

    test('12 kg → three-quarters', () {
      final rx = prescribeCotrimoxazole(12.0);
      expect(rx!.doseDescription, contains('three-quarters'));
    });

    test('16 kg → 1 adult tablet', () {
      final rx = prescribeCotrimoxazole(16.0);
      expect(rx!.doseDescription, contains('1 adult'));
    });
  });

  // ==========================================================================
  // ACT — IMCI Chart Booklet p.19
  // ==========================================================================

  group('prescribeACT — antimalarial weight-band dosing', () {
    test('< 5 kg → not recommended (null)', () {
      final rx = prescribeACT(4.5);
      expect(rx, isNull);
    });

    test('5 kg → 1 tablet per dose', () {
      final rx = prescribeACT(5.0);
      expect(rx, isNotNull);
      expect(rx!.doseDescription, contains('1 tablet'));
      expect(rx.durationDays, 3);
    });

    test('14.9 kg → still 1 tablet', () {
      final rx = prescribeACT(14.9);
      expect(rx!.doseDescription, contains('1 tablet'));
    });

    test('15.0 kg → 2 tablets (boundary crossover)', () {
      final rx = prescribeACT(15.0);
      expect(rx!.doseDescription, contains('2 tablets'));
    });

    test('25.0 kg → 3 tablets', () {
      final rx = prescribeACT(25.0);
      expect(rx!.doseDescription, contains('3 tablets'));
    });

    test('preparation mentions 6 doses over 3 days', () {
      final rx = prescribeACT(10.0);
      expect(rx!.preparation, contains('6 doses'));
    });

    test('preparation mentions take with food', () {
      final rx = prescribeACT(10.0);
      expect(rx!.preparation, contains('food'));
    });
  });

  // ==========================================================================
  // PARACETAMOL — IMCI Chart Booklet p.20
  // ==========================================================================

  group('prescribeParacetamol — weight-band dosing', () {
    test('4 kg → 2.5 ml', () {
      final rx = prescribeParacetamol(4.0);
      expect(rx, isNotNull);
      expect(rx!.doseDescription, contains('2.5 ml'));
    });

    test('8 kg → 4 ml', () {
      final rx = prescribeParacetamol(8.0);
      expect(rx!.doseDescription, contains('4 ml'));
    });

    test('12 kg → 6 ml', () {
      final rx = prescribeParacetamol(12.0);
      expect(rx!.doseDescription, contains('6 ml'));
    });

    test('17 kg → 8 ml', () {
      final rx = prescribeParacetamol(17.0);
      expect(rx!.doseDescription, contains('8 ml'));
    });

    test('max 4 times per day', () {
      final rx = prescribeParacetamol(10.0);
      expect(rx!.timesPerDay, 4);
    });

    test('only when fever', () {
      final rx = prescribeParacetamol(10.0);
      expect(rx!.preparation, contains('fever'));
    });
  });

  // ==========================================================================
  // VITAMIN A — IMCI Chart Booklet p.21
  // ==========================================================================

  group('prescribeVitaminA — age-based dosing', () {
    test('3 months → 50,000 IU', () {
      final rx = prescribeVitaminA(3);
      expect(rx, isNotNull);
      expect(rx!.doseMg, 50000);
    });

    test('5 months → 50,000 IU (boundary)', () {
      final rx = prescribeVitaminA(5);
      expect(rx!.doseMg, 50000);
    });

    test('6 months → 100,000 IU (boundary crossover)', () {
      final rx = prescribeVitaminA(6);
      expect(rx!.doseMg, 100000);
    });

    test('11 months → 100,000 IU', () {
      final rx = prescribeVitaminA(11);
      expect(rx!.doseMg, 100000);
    });

    test('12 months → 200,000 IU (boundary crossover)', () {
      final rx = prescribeVitaminA(12);
      expect(rx!.doseMg, 200000);
    });

    test('48 months → 200,000 IU', () {
      final rx = prescribeVitaminA(48);
      expect(rx!.doseMg, 200000);
    });

    test('single dose', () {
      final rx = prescribeVitaminA(24);
      expect(rx!.timesPerDay, 1);
      expect(rx.durationDays, 1);
    });
  });

  // ==========================================================================
  // ZINC — WHO/UNICEF Joint Statement
  // ==========================================================================

  group('prescribeZinc — age-based dosing', () {
    test('3 months → 10 mg/day', () {
      final rx = prescribeZinc(3);
      expect(rx.doseMg, 10.0);
      expect(rx.doseDescription, contains('half'));
    });

    test('5 months → 10 mg/day (boundary)', () {
      final rx = prescribeZinc(5);
      expect(rx.doseMg, 10.0);
    });

    test('6 months → 20 mg/day (boundary crossover)', () {
      final rx = prescribeZinc(6);
      expect(rx.doseMg, 20.0);
      expect(rx.doseDescription, contains('1 tablet'));
    });

    test('24 months → 20 mg/day', () {
      final rx = prescribeZinc(24);
      expect(rx.doseMg, 20.0);
    });

    test('14 days duration', () {
      final rx = prescribeZinc(12);
      expect(rx.durationDays, 14);
    });

    test('preparation mentions continue after diarrhea stops', () {
      final rx = prescribeZinc(12);
      expect(rx.preparation, contains('diarrhea stops'));
    });
  });

  // ==========================================================================
  // MEBENDAZOLE — IMCI Chart Booklet p.21
  // ==========================================================================

  group('prescribeMebendazole — age gate', () {
    test('11 months → null (too young)', () {
      final rx = prescribeMebendazole(11);
      expect(rx, isNull);
    });

    test('12 months → 500 mg single dose', () {
      final rx = prescribeMebendazole(12);
      expect(rx, isNotNull);
      expect(rx!.doseMg, 500);
      expect(rx.durationDays, 1);
    });

    test('36 months → 500 mg single dose', () {
      final rx = prescribeMebendazole(36);
      expect(rx!.doseMg, 500);
    });
  });

  // ==========================================================================
  // ORS PLAN CALCULATION — IMCI Chart Booklet p.16-17
  // ==========================================================================

  group('calculateOrsPlan', () {
    test('severe dehydration → Plan C (100 ml/kg)', () {
      final plan = calculateOrsPlan(
        dehydrationLevel: ClassificationType.severeDehydration,
        weightKg: 10.0,
        ageMonths: 12,
      );
      expect(plan.planType, 'C');
      expect(plan.volumeMl, 1000.0); // 100 × 10
      expect(plan.frequency, contains('URGENT'));
    });

    test('some dehydration → Plan B (75 ml/kg over 4h)', () {
      final plan = calculateOrsPlan(
        dehydrationLevel: ClassificationType.someDehydration,
        weightKg: 10.0,
        ageMonths: 12,
      );
      expect(plan.planType, 'B');
      expect(plan.volumeMl, 750.0); // 75 × 10
      expect(plan.frequency, contains('4 hours'));
    });

    test('Plan B — 8 kg child → 600 ml', () {
      final plan = calculateOrsPlan(
        dehydrationLevel: ClassificationType.someDehydration,
        weightKg: 8.0,
        ageMonths: 9,
      );
      expect(plan.volumeMl, 600.0);
    });

    test('no dehydration → Plan A (per stool)', () {
      final plan = calculateOrsPlan(
        dehydrationLevel: ClassificationType.noDehydration,
        weightKg: 10.0,
        ageMonths: 12,
      );
      expect(plan.planType, 'A');
      expect(plan.frequency, contains('each loose stool'));
    });

    test('Plan A — infant (<24mo) → 75 ml per stool', () {
      final plan = calculateOrsPlan(
        dehydrationLevel: ClassificationType.noDehydration,
        weightKg: 8.0,
        ageMonths: 10,
      );
      expect(plan.volumeMl, 75.0);
    });

    test('Plan A — older child (≥24mo) → 150 ml per stool', () {
      final plan = calculateOrsPlan(
        dehydrationLevel: ClassificationType.noDehydration,
        weightKg: 12.0,
        ageMonths: 30,
      );
      expect(plan.volumeMl, 150.0);
    });

    test('zinc dose — infant < 6mo → 10 mg', () {
      final plan = calculateOrsPlan(
        dehydrationLevel: ClassificationType.someDehydration,
        weightKg: 5.0,
        ageMonths: 4,
      );
      expect(plan.zincDoseMg, 10.0);
    });

    test('zinc dose — child ≥ 6mo → 20 mg', () {
      final plan = calculateOrsPlan(
        dehydrationLevel: ClassificationType.someDehydration,
        weightKg: 8.0,
        ageMonths: 9,
      );
      expect(plan.zincDoseMg, 20.0);
    });

    test('homemade recipe available', () {
      expect(OrsGuide.homemadeRecipe, contains('sugar'));
      expect(OrsGuide.homemadeRecipe, contains('salt'));
      expect(OrsGuide.homemadeRecipe, contains('1 liter'));
    });
  });

  // ==========================================================================
  // FULL TREATMENT PLAN GENERATION
  // ==========================================================================

  group('generateTreatmentPlan — integration', () {
    test('pneumonia → amoxicillin prescribed', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.pneumonia,
            severity: Severity.yellow,
            referral: ReferralUrgency.within24h,
            reasoning: 'test',
          ),
        ],
        ageMonths: 18,
        weightKg: 11.0,
      );
      expect(plan.medicines.any((m) => m.medicineName == 'Amoxicillin'), isTrue);
      expect(plan.overallSeverity, Severity.yellow);
      expect(plan.followUp, contains('2 days'));
    });

    test('severe pneumonia → pre-referral first dose', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.severePneumonia,
            severity: Severity.red,
            referral: ReferralUrgency.immediate,
            reasoning: 'test',
          ),
        ],
        ageMonths: 12,
        weightKg: 9.0,
      );
      expect(plan.preReferralActions.any((a) => a.contains('amoxicillin')), isTrue);
      expect(plan.preReferralActions.any((a) => a.contains('IMMEDIATELY')), isTrue);
      expect(plan.overallSeverity, Severity.red);
    });

    test('diarrhea with some dehydration → ORS Plan B + zinc', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.someDehydration,
            severity: Severity.yellow,
            referral: ReferralUrgency.within24h,
            reasoning: 'test',
          ),
        ],
        ageMonths: 18,
        weightKg: 11.0,
      );
      expect(plan.orsGuide, isNotNull);
      expect(plan.orsGuide!.planType, 'B');
      expect(plan.orsGuide!.volumeMl, 825.0); // 75 × 11
      expect(plan.medicines.any((m) => m.medicineName == 'Zinc'), isTrue);
    });

    test('malaria → ACT + paracetamol', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.malaria,
            severity: Severity.yellow,
            referral: ReferralUrgency.within24h,
            reasoning: 'test',
          ),
        ],
        ageMonths: 24,
        weightKg: 12.0,
      );
      expect(plan.medicines.any((m) => m.medicineName.contains('ACT')), isTrue);
      expect(plan.medicines.any((m) => m.medicineName == 'Paracetamol'), isTrue);
    });

    test('measles → paracetamol + vitamin A', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.measles,
            severity: Severity.yellow,
            referral: ReferralUrgency.within24h,
            reasoning: 'test',
          ),
        ],
        ageMonths: 24,
        weightKg: 12.0,
      );
      expect(plan.medicines.any((m) => m.medicineName == 'Vitamin A'), isTrue);
      expect(plan.medicines.any((m) => m.medicineName == 'Paracetamol'), isTrue);
    });

    test('severe malnutrition → pre-referral + vitamin A', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.severeMalnutrition,
            severity: Severity.red,
            referral: ReferralUrgency.immediate,
            reasoning: 'test',
          ),
        ],
        ageMonths: 18,
        weightKg: 7.0,
      );
      expect(plan.medicines.any((m) => m.medicineName == 'Vitamin A'), isTrue);
      expect(plan.preReferralActions.any((a) => a.contains('warm')), isTrue);
      expect(plan.overallSeverity, Severity.red);
    });

    test('moderate malnutrition → mebendazole + nutrition counseling', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.moderateMalnutrition,
            severity: Severity.yellow,
            referral: ReferralUrgency.within24h,
            reasoning: 'test',
          ),
        ],
        ageMonths: 24,
        weightKg: 10.0,
      );
      expect(plan.medicines.any((m) => m.medicineName == 'Mebendazole'), isTrue);
      expect(plan.homeCare.any((h) => h.contains('extra meal')), isTrue);
    });

    test('moderate malnutrition at 10 months → no mebendazole (too young)', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.moderateMalnutrition,
            severity: Severity.yellow,
            referral: ReferralUrgency.within24h,
            reasoning: 'test',
          ),
        ],
        ageMonths: 10,
        weightKg: 7.0,
      );
      expect(plan.medicines.any((m) => m.medicineName == 'Mebendazole'), isFalse);
    });

    test('dysentery → cotrimoxazole', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.dysentery,
            severity: Severity.yellow,
            referral: ReferralUrgency.within24h,
            reasoning: 'test',
          ),
        ],
        ageMonths: 24,
        weightKg: 12.0,
      );
      expect(plan.medicines.any((m) => m.medicineName == 'Cotrimoxazole'), isTrue);
    });

    test('green severity → follow up in 5 days', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.noPneumoniaCoughOrCold,
            severity: Severity.green,
            referral: ReferralUrgency.none,
            reasoning: 'test',
          ),
        ],
        ageMonths: 18,
        weightKg: 11.0,
      );
      expect(plan.followUp, contains('5 days'));
      expect(plan.overallSeverity, Severity.green);
    });

    test('always includes return-immediately signs', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.healthy,
            severity: Severity.green,
            referral: ReferralUrgency.none,
            reasoning: 'test',
          ),
        ],
        ageMonths: 18,
        weightKg: 11.0,
      );
      expect(plan.returnImmediatelyIf, isNotEmpty);
      expect(plan.returnImmediatelyIf.any((s) => s.contains('convulsions')), isTrue);
    });

    test('weight 0 → uses age-based estimation', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.pneumonia,
            severity: Severity.yellow,
            referral: ReferralUrgency.within24h,
            reasoning: 'test',
          ),
        ],
        ageMonths: 12,
        weightKg: 0, // Unknown weight
      );
      // 12 months → estimated 9.5 kg → 1 tablet band (6-10 kg)
      final amox = plan.medicines.firstWhere((m) => m.medicineName == 'Amoxicillin');
      expect(amox.doseMg, 250.0); // 1 tablet
    });

    test('multiple conditions → all treated', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.pneumonia,
            severity: Severity.yellow,
            referral: ReferralUrgency.within24h,
            reasoning: 'test',
          ),
          const DomainClassification(
            classification: ClassificationType.someDehydration,
            severity: Severity.yellow,
            referral: ReferralUrgency.within24h,
            reasoning: 'test',
          ),
          const DomainClassification(
            classification: ClassificationType.malaria,
            severity: Severity.yellow,
            referral: ReferralUrgency.within24h,
            reasoning: 'test',
          ),
        ],
        ageMonths: 24,
        weightKg: 12.0,
      );
      expect(plan.medicines.any((m) => m.medicineName == 'Amoxicillin'), isTrue);
      expect(plan.medicines.any((m) => m.medicineName == 'Zinc'), isTrue);
      expect(plan.medicines.any((m) => m.medicineName.contains('ACT')), isTrue);
      expect(plan.medicines.any((m) => m.medicineName == 'Paracetamol'), isTrue);
      expect(plan.orsGuide, isNotNull);
    });

    test('worst severity wins — red overrides yellow', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.severePneumonia,
            severity: Severity.red,
            referral: ReferralUrgency.immediate,
            reasoning: 'test',
          ),
          const DomainClassification(
            classification: ClassificationType.someDehydration,
            severity: Severity.yellow,
            referral: ReferralUrgency.within24h,
            reasoning: 'test',
          ),
        ],
        ageMonths: 18,
        weightKg: 11.0,
      );
      expect(plan.overallSeverity, Severity.red);
      expect(plan.followUp, contains('IMMEDIATELY'));
    });

    test('always includes breastfeeding advice', () {
      final plan = generateTreatmentPlan(
        classifications: [
          const DomainClassification(
            classification: ClassificationType.healthy,
            severity: Severity.green,
            referral: ReferralUrgency.none,
            reasoning: 'test',
          ),
        ],
        ageMonths: 12,
        weightKg: 9.0,
      );
      expect(
        plan.homeCare.any((h) => h.toLowerCase().contains('breastfeed') || h.toLowerCase().contains('feeding')),
        isTrue,
      );
    });
  });
}
