/// WHO IMCI Treatment Protocol — deterministic dosing logic.
///
/// THIS IS THE MEDICAL SAFETY BOUNDARY FOR TREATMENT.
///
/// Every function in this module is pure: same input → same output, always.
/// Every dose is from the WHO IMCI Chart Booklet with page citations.
/// This module MUST NOT import inference code or call any AI.
///
/// Reference: WHO IMCI Chart Booklet (2014 revision, reaffirmed 2023)
/// https://www.who.int/publications/i/item/9789241506823
/// WHO/UNICEF Joint Statement on ORS + Zinc (2004, reaffirmed)
/// WHO Revised Classification and Treatment of Pneumonia in Children (2014)
library;

import 'package:flutter/foundation.dart';
import 'imci_protocol.dart';
import 'imci_types.dart';

// ============================================================================
// WEIGHT-BAND DOSING — WHO IMCI Chart Booklet p.18-21
// ============================================================================

/// A single weight band mapping to a dose.
@immutable
class WeightBand {
  final double minKg;
  final double maxKg; // exclusive
  final double doseAmount;
  final String doseDescription; // human-friendly: "1 tablet", "2.5 ml"

  const WeightBand({
    required this.minKg,
    required this.maxKg,
    required this.doseAmount,
    required this.doseDescription,
  });

  bool matches(double weightKg) => weightKg >= minKg && weightKg < maxKg;
}

/// WHO median weight-for-age (months). Used as fallback when weight unknown.
/// Source: WHO Child Growth Standards (2006)
double estimateWeightFromAge(int ageMonths) {
  // Simplified WHO median weights (boys/girls average)
  if (ageMonths <= 0) return 3.5;
  if (ageMonths <= 1) return 4.5;
  if (ageMonths <= 3) return 6.0;
  if (ageMonths <= 6) return 7.5;
  if (ageMonths <= 9) return 8.5;
  if (ageMonths <= 12) return 9.5;
  if (ageMonths <= 18) return 11.0;
  if (ageMonths <= 24) return 12.0;
  if (ageMonths <= 36) return 14.0;
  if (ageMonths <= 48) return 16.0;
  return 18.0; // 49-59 months
}

// ============================================================================
// MEDICINE PRESCRIPTIONS
// ============================================================================

/// A single medicine prescription with exact dosing.
@immutable
class MedicinePrescription {
  /// Drug name (international nonproprietary name).
  final String medicineName;

  /// Formulation details.
  final String formulation;

  /// Human-readable dose: "1 tablet", "4 ml".
  final String doseDescription;

  /// Machine-precise dose in mg.
  final double doseMg;

  /// How many times per day.
  final int timesPerDay;

  /// Total days of treatment.
  final int durationDays;

  /// How to prepare / administer.
  final String preparation;

  /// WHO source reference.
  final String whoReference;

  const MedicinePrescription({
    required this.medicineName,
    required this.formulation,
    required this.doseDescription,
    required this.doseMg,
    required this.timesPerDay,
    required this.durationDays,
    required this.preparation,
    required this.whoReference,
  });
}

// ============================================================================
// ORS REHYDRATION GUIDE — WHO IMCI Chart Booklet p.16-17
// ============================================================================

/// ORS rehydration plan with exact volumes.
@immutable
class OrsGuide {
  /// Plan type: "A" (home), "B" (clinic 4hr), "C" (emergency IV/referral).
  final String planType;

  /// Exact ORS volume in ml (for Plan B = 75 × weightKg).
  final double volumeMl;

  /// How often: "after each loose stool" or "over 4 hours".
  final String frequency;

  /// Zinc dose in mg (10 or 20).
  final double zincDoseMg;

  /// Zinc treatment duration in days.
  final int zincDays;

  /// Whether to include homemade ORS recipe.
  final bool includeHomemadeRecipe;

  /// WHO source reference.
  final String whoReference;

  const OrsGuide({
    required this.planType,
    required this.volumeMl,
    required this.frequency,
    required this.zincDoseMg,
    this.zincDays = 14,
    this.includeHomemadeRecipe = true,
    this.whoReference = 'WHO IMCI Chart Booklet p.16-17',
  });

  /// Homemade ORS recipe — WHO-approved emergency formula.
  static const String homemadeRecipe =
      '6 level teaspoons of sugar + half a teaspoon of salt '
      'in 1 liter of clean water. Stir until dissolved.';
}

// ============================================================================
// TREATMENT PLAN — Complete output
// ============================================================================

/// Complete treatment plan for a child.
@immutable
class TreatmentPlan {
  /// Prescribed medicines with exact doses.
  final List<MedicinePrescription> medicines;

  /// ORS rehydration guide (if diarrhea present).
  final OrsGuide? orsGuide;

  /// Pre-referral actions for RED severity.
  final List<String> preReferralActions;

  /// Home care instructions.
  final List<String> homeCare;

  /// Follow-up schedule.
  final String followUp;

  /// Danger signs — return immediately if any appear.
  final List<String> returnImmediatelyIf;

  /// Overall severity driving this plan.
  final Severity overallSeverity;

  const TreatmentPlan({
    required this.medicines,
    this.orsGuide,
    this.preReferralActions = const [],
    this.homeCare = const [],
    required this.followUp,
    this.returnImmediatelyIf = const [],
    required this.overallSeverity,
  });
}

// ============================================================================
// AMOXICILLIN — First-line oral antibiotic for pneumonia
// WHO IMCI Chart Booklet p.18 / WHO Revised Pneumonia Classification 2014
// ============================================================================

/// Amoxicillin 250mg dispersible tablet — weight-band dosing.
/// Dose: 25 mg/kg twice daily for 5 days.
/// Source: WHO IMCI Chart Booklet p.18
const List<WeightBand> amoxicillinBands = [
  WeightBand(minKg: 0, maxKg: 6, doseAmount: 0.5, doseDescription: 'half a tablet'),
  WeightBand(minKg: 6, maxKg: 10, doseAmount: 1.0, doseDescription: '1 tablet'),
  WeightBand(minKg: 10, maxKg: 14, doseAmount: 2.0, doseDescription: '2 tablets'),
  WeightBand(minKg: 14, maxKg: 100, doseAmount: 3.0, doseDescription: '3 tablets'),
];

MedicinePrescription? prescribeAmoxicillin(double weightKg) {
  for (final band in amoxicillinBands) {
    if (band.matches(weightKg)) {
      return MedicinePrescription(
        medicineName: 'Amoxicillin',
        formulation: '250mg dispersible tablet',
        doseDescription: '${band.doseDescription} twice daily',
        doseMg: band.doseAmount * 250,
        timesPerDay: 2,
        durationDays: 5,
        preparation: 'Dissolve tablet in a small amount of clean water or '
            'breast milk. Give the full dose. '
            'Complete all 5 days even if the child improves.',
        whoReference: 'WHO IMCI Chart Booklet p.18',
      );
    }
  }
  return null;
}

// ============================================================================
// COTRIMOXAZOLE — Oral antibiotic for dysentery
// WHO IMCI Chart Booklet p.18
// ============================================================================

/// Cotrimoxazole adult tablet (80mg TMP / 400mg SMX) — weight-band dosing.
/// Source: WHO IMCI Chart Booklet p.18
const List<WeightBand> cotrimoxazoleBands = [
  WeightBand(minKg: 0, maxKg: 6, doseAmount: 0.25, doseDescription: 'quarter of adult tablet'),
  WeightBand(minKg: 6, maxKg: 10, doseAmount: 0.5, doseDescription: 'half of adult tablet'),
  WeightBand(minKg: 10, maxKg: 14, doseAmount: 0.75, doseDescription: 'three-quarters of adult tablet'),
  WeightBand(minKg: 14, maxKg: 100, doseAmount: 1.0, doseDescription: '1 adult tablet'),
];

MedicinePrescription? prescribeCotrimoxazole(double weightKg) {
  for (final band in cotrimoxazoleBands) {
    if (band.matches(weightKg)) {
      return MedicinePrescription(
        medicineName: 'Cotrimoxazole',
        formulation: 'Adult tablet (80mg TMP / 400mg SMX)',
        doseDescription: '${band.doseDescription} twice daily',
        doseMg: band.doseAmount * 80, // TMP component
        timesPerDay: 2,
        durationDays: 5,
        preparation: 'Crush the tablet portion and mix with a small '
            'amount of clean water. Give twice daily for 5 days.',
        whoReference: 'WHO IMCI Chart Booklet p.18',
      );
    }
  }
  return null;
}

// ============================================================================
// ARTEMETHER-LUMEFANTRINE (ACT) — First-line antimalarial
// WHO IMCI Chart Booklet p.19
// ============================================================================

/// AL tablet (20mg artemether / 120mg lumefantrine) — weight-band dosing.
/// Regimen: 6 doses over 3 days (0h, 8h, 24h, 36h, 48h, 60h).
/// Source: WHO IMCI Chart Booklet p.19
const List<WeightBand> actBands = [
  WeightBand(minKg: 5, maxKg: 15, doseAmount: 1.0, doseDescription: '1 tablet per dose'),
  WeightBand(minKg: 15, maxKg: 25, doseAmount: 2.0, doseDescription: '2 tablets per dose'),
  WeightBand(minKg: 25, maxKg: 100, doseAmount: 3.0, doseDescription: '3 tablets per dose'),
];

MedicinePrescription? prescribeACT(double weightKg) {
  if (weightKg < 5) return null; // Not recommended for children <5 kg
  for (final band in actBands) {
    if (band.matches(weightKg)) {
      return MedicinePrescription(
        medicineName: 'Artemether-Lumefantrine (ACT)',
        formulation: 'Tablet (20mg/120mg)',
        doseDescription: '${band.doseDescription}, 6 doses over 3 days',
        doseMg: band.doseAmount * 20, // Artemether component
        timesPerDay: 2,
        durationDays: 3,
        preparation: 'Give with food or milk. '
            'First dose now, second dose after 8 hours, '
            'then one dose morning and evening for 2 more days. '
            '6 doses total. Complete all doses.',
        whoReference: 'WHO IMCI Chart Booklet p.19',
      );
    }
  }
  return null;
}

// ============================================================================
// PARACETAMOL — Fever management
// WHO IMCI Chart Booklet p.20
// ============================================================================

/// Paracetamol 120mg/5ml syrup — weight-band dosing.
/// Dose: 15 mg/kg, 3-4 times daily. Max 60 mg/kg/day.
/// Source: WHO IMCI Chart Booklet p.20
const List<WeightBand> paracetamolSyrupBands = [
  WeightBand(minKg: 0, maxKg: 6, doseAmount: 2.5, doseDescription: '2.5 ml (half teaspoon)'),
  WeightBand(minKg: 6, maxKg: 10, doseAmount: 4.0, doseDescription: '4 ml'),
  WeightBand(minKg: 10, maxKg: 15, doseAmount: 6.0, doseDescription: '6 ml (one teaspoon)'),
  WeightBand(minKg: 15, maxKg: 100, doseAmount: 8.0, doseDescription: '8 ml'),
];

MedicinePrescription? prescribeParacetamol(double weightKg) {
  for (final band in paracetamolSyrupBands) {
    if (band.matches(weightKg)) {
      return MedicinePrescription(
        medicineName: 'Paracetamol',
        formulation: '120mg/5ml syrup',
        doseDescription: '${band.doseDescription} every 6 hours if fever',
        doseMg: band.doseAmount * 24, // 120mg per 5ml
        timesPerDay: 4,
        durationDays: 3,
        preparation: 'Give only when the child feels hot or has fever. '
            'Wait at least 6 hours between doses. '
            'Do not give more than 4 doses in one day.',
        whoReference: 'WHO IMCI Chart Booklet p.20',
      );
    }
  }
  return null;
}

// ============================================================================
// VITAMIN A — Measles, malnutrition, persistent diarrhea
// WHO IMCI Chart Booklet p.21
// ============================================================================

/// Vitamin A capsule — age-based dosing.
/// Source: WHO IMCI Chart Booklet p.21
MedicinePrescription? prescribeVitaminA(int ageMonths) {
  if (ageMonths < 6) {
    return const MedicinePrescription(
      medicineName: 'Vitamin A',
      formulation: '50,000 IU capsule',
      doseDescription: '50,000 IU — one dose now',
      doseMg: 50000,
      timesPerDay: 1,
      durationDays: 1,
      preparation: 'Cut the tip of the capsule and squeeze the liquid '
          'directly into the child\'s mouth.',
      whoReference: 'WHO IMCI Chart Booklet p.21',
    );
  }
  if (ageMonths <= 11) {
    return const MedicinePrescription(
      medicineName: 'Vitamin A',
      formulation: '100,000 IU capsule',
      doseDescription: '100,000 IU — one dose now',
      doseMg: 100000,
      timesPerDay: 1,
      durationDays: 1,
      preparation: 'Cut the tip of the capsule and squeeze the liquid '
          'directly into the child\'s mouth.',
      whoReference: 'WHO IMCI Chart Booklet p.21',
    );
  }
  // 12-59 months
  return const MedicinePrescription(
    medicineName: 'Vitamin A',
    formulation: '200,000 IU capsule',
    doseDescription: '200,000 IU — one dose now',
    doseMg: 200000,
    timesPerDay: 1,
    durationDays: 1,
    preparation: 'Cut the tip of the capsule and squeeze the liquid '
        'directly into the child\'s mouth.',
    whoReference: 'WHO IMCI Chart Booklet p.21',
  );
}

// ============================================================================
// ZINC — Diarrhea treatment adjunct
// WHO/UNICEF Joint Statement 2004 (reaffirmed)
// ============================================================================

/// Zinc supplementation — age-based dosing.
/// <6 months: 10 mg/day for 10-14 days
/// ≥6 months: 20 mg/day for 10-14 days
/// Source: WHO/UNICEF Joint Statement on ORS + Zinc
MedicinePrescription prescribeZinc(int ageMonths) {
  final dose = ageMonths < 6 ? 10.0 : 20.0;
  final desc = ageMonths < 6 ? 'half a tablet' : '1 tablet';
  return MedicinePrescription(
    medicineName: 'Zinc',
    formulation: '20mg dispersible tablet',
    doseDescription: '$desc daily for 14 days',
    doseMg: dose,
    timesPerDay: 1,
    durationDays: 14,
    preparation: 'Dissolve the tablet in a small amount of breast milk '
        'or clean water in a cup. Give the full amount. '
        'Continue for 14 days even after diarrhea stops.',
    whoReference: 'WHO/UNICEF Joint Statement on Zinc',
  );
}

// ============================================================================
// MEBENDAZOLE — Deworming
// WHO IMCI Chart Booklet p.21
// ============================================================================

/// Mebendazole — single dose if ≥12 months old.
/// Source: WHO IMCI Chart Booklet p.21
MedicinePrescription? prescribeMebendazole(int ageMonths) {
  if (ageMonths < 12) return null;
  return const MedicinePrescription(
    medicineName: 'Mebendazole',
    formulation: '500mg tablet',
    doseDescription: '1 tablet — single dose now',
    doseMg: 500,
    timesPerDay: 1,
    durationDays: 1,
    preparation: 'The child can chew the tablet or it can be crushed '
        'and mixed with food.',
    whoReference: 'WHO IMCI Chart Booklet p.21',
  );
}

// ============================================================================
// ORS PLAN CALCULATION — WHO IMCI Chart Booklet p.16-17
// ============================================================================

/// Calculate ORS rehydration plan based on dehydration classification.
///
/// Plan A: No dehydration — home treatment.
///   <2yr: 50-100 ml after each loose stool (~500 ml/day)
///   2-5yr: 100-200 ml after each loose stool (~1000 ml/day)
///
/// Plan B: Some dehydration — 4-hour clinic treatment.
///   75 ml/kg over 4 hours.
///
/// Plan C: Severe dehydration — emergency referral for IV fluids.
///   100 ml/kg IV Ringer's Lactate.
///
/// Source: WHO IMCI Chart Booklet p.16-17
OrsGuide calculateOrsPlan({
  required ClassificationType dehydrationLevel,
  required double weightKg,
  required int ageMonths,
}) {
  final zincDose = ageMonths < 6 ? 10.0 : 20.0;

  switch (dehydrationLevel) {
    case ClassificationType.severeDehydration:
      return OrsGuide(
        planType: 'C',
        volumeMl: weightKg * 100, // 100 ml/kg IV
        frequency: 'URGENT: IV fluids at health facility',
        zincDoseMg: zincDose,
        includeHomemadeRecipe: false,
        whoReference: 'WHO IMCI Chart Booklet p.17 — Plan C',
      );

    case ClassificationType.someDehydration:
      return OrsGuide(
        planType: 'B',
        volumeMl: weightKg * 75, // 75 ml/kg over 4 hours
        frequency: 'over 4 hours — small sips frequently',
        zincDoseMg: zincDose,
        whoReference: 'WHO IMCI Chart Booklet p.16 — Plan B',
      );

    default:
      // Plan A — no dehydration or mild
      final volume = ageMonths < 24 ? 75.0 : 150.0; // midpoint of range
      return OrsGuide(
        planType: 'A',
        volumeMl: volume,
        frequency: 'after each loose stool',
        zincDoseMg: zincDose,
        whoReference: 'WHO IMCI Chart Booklet p.16 — Plan A',
      );
  }
}

// ============================================================================
// RETURN IMMEDIATELY SIGNS — Universal for all classifications
// ============================================================================

/// Danger signs that require immediate return to health facility.
/// Source: WHO IMCI Chart Booklet p.6 — "When to return immediately"
const List<String> universalReturnSigns = [
  'Child is unable to drink or breastfeed',
  'Child becomes sicker or develops a fever',
  'Child has fast or difficult breathing',
  'Child has blood in the stool',
  'Child is drinking poorly',
  'Child has convulsions (fits)',
];

// ============================================================================
// MASTER TREATMENT PLAN GENERATOR
// ============================================================================

/// Generate a complete treatment plan from IMCI classifications.
///
/// This is the master function that routes each classification to
/// the appropriate medicines and dosing. All dosing is deterministic —
/// pure lookup tables from WHO IMCI Chart Booklet.
///
/// [classifications] — List of domain classifications from imci_protocol.dart.
/// [ageMonths] — Child's age in months (2-59).
/// [weightKg] — Child's weight in kg. If 0, estimated from age.
TreatmentPlan generateTreatmentPlan({
  required List<DomainClassification> classifications,
  required int ageMonths,
  double weightKg = 0,
}) {
  // Estimate weight if not provided
  final weight = weightKg > 0 ? weightKg : estimateWeightFromAge(ageMonths);

  final medicines = <MedicinePrescription>[];
  final preReferral = <String>[];
  final homeCare = <String>[];
  OrsGuide? orsGuide;

  // Determine overall severity
  Severity worstSeverity = Severity.green;
  for (final c in classifications) {
    if (c.severity == Severity.red) {
      worstSeverity = Severity.red;
      break;
    }
    if (c.severity == Severity.yellow) {
      worstSeverity = Severity.yellow;
    }
  }

  // Track which conditions are present
  final types = classifications.map((c) => c.classification).toSet();

  // ── PNEUMONIA / SEVERE PNEUMONIA ──
  if (types.contains(ClassificationType.severePneumonia)) {
    // Pre-referral first dose
    final amox = prescribeAmoxicillin(weight);
    if (amox != null) {
      preReferral.add(
        'Give first dose of amoxicillin (${amox.doseDescription.split(' twice').first}) '
        'NOW before going to the health facility',
      );
    }
    preReferral.add('Keep the child warm');
    preReferral.add('Go to the health facility IMMEDIATELY');
  } else if (types.contains(ClassificationType.pneumonia)) {
    final amox = prescribeAmoxicillin(weight);
    if (amox != null) medicines.add(amox);
    homeCare.add('Keep the child warm and continue feeding');
    homeCare.add('Clear the nose if blocked — use a clean cloth');
    homeCare.add('Watch for fast or difficult breathing');
  }

  // ── DIARRHEA / DEHYDRATION ──
  if (types.contains(ClassificationType.severeDehydration)) {
    orsGuide = calculateOrsPlan(
      dehydrationLevel: ClassificationType.severeDehydration,
      weightKg: weight,
      ageMonths: ageMonths,
    );
    preReferral.add('Start giving ORS on the way to the health facility');
    preReferral.add('Go to the health facility IMMEDIATELY for IV fluids');
  } else if (types.contains(ClassificationType.someDehydration)) {
    orsGuide = calculateOrsPlan(
      dehydrationLevel: ClassificationType.someDehydration,
      weightKg: weight,
      ageMonths: ageMonths,
    );
    medicines.add(prescribeZinc(ageMonths));
    homeCare.add('Continue breastfeeding');
    homeCare.add('Give extra fluids');
  } else if (types.contains(ClassificationType.noDehydration) ||
      types.contains(ClassificationType.persistentDiarrhea)) {
    orsGuide = calculateOrsPlan(
      dehydrationLevel: ClassificationType.noDehydration,
      weightKg: weight,
      ageMonths: ageMonths,
    );
    medicines.add(prescribeZinc(ageMonths));
    homeCare.add('Continue breastfeeding and give extra fluids');
  }

  // ── DYSENTERY ──
  if (types.contains(ClassificationType.dysentery)) {
    final cotri = prescribeCotrimoxazole(weight);
    if (cotri != null) medicines.add(cotri);
  }

  // ── MALARIA ──
  if (types.contains(ClassificationType.malaria)) {
    final act = prescribeACT(weight);
    if (act != null) medicines.add(act);
  }

  // ── VERY SEVERE FEBRILE DISEASE ──
  if (types.contains(ClassificationType.verySevereFebrileDisease)) {
    final amox = prescribeAmoxicillin(weight);
    if (amox != null) {
      preReferral.add(
        'Give first dose of amoxicillin (${amox.doseDescription.split(' twice').first}) '
        'NOW before referral',
      );
    }
    preReferral.add('Go to the health facility IMMEDIATELY — possible meningitis');
  }

  // ── FEVER (any) → Paracetamol ──
  if (types.contains(ClassificationType.malaria) ||
      types.contains(ClassificationType.feverNoMalaria) ||
      types.contains(ClassificationType.verySevereFebrileDisease) ||
      types.contains(ClassificationType.measles) ||
      types.contains(ClassificationType.measlesWithComplications)) {
    final para = prescribeParacetamol(weight);
    if (para != null) medicines.add(para);
  }

  // ── MEASLES → Vitamin A ──
  if (types.contains(ClassificationType.measles) ||
      types.contains(ClassificationType.measlesWithComplications)) {
    final vitA = prescribeVitaminA(ageMonths);
    if (vitA != null) medicines.add(vitA);
  }

  // ── SEVERE MALNUTRITION ──
  if (types.contains(ClassificationType.severeMalnutrition)) {
    final vitA = prescribeVitaminA(ageMonths);
    if (vitA != null && !medicines.any((m) => m.medicineName == 'Vitamin A')) {
      medicines.add(vitA);
    }
    preReferral.add('Give first feed if the child can eat');
    preReferral.add('Keep the child warm — wrap in a blanket');
    preReferral.add('Go to the health facility for therapeutic feeding');
  }

  // ── MODERATE MALNUTRITION → Nutrition counseling + deworming ──
  if (types.contains(ClassificationType.moderateMalnutrition)) {
    final meb = prescribeMebendazole(ageMonths);
    if (meb != null) medicines.add(meb);
    homeCare.add('Give the child an extra meal each day');
    homeCare.add('Give nutrient-rich foods: eggs, beans, groundnuts, dark green vegetables');
    homeCare.add('Continue breastfeeding if under 2 years');
  }

  // ── PERSISTENT DIARRHEA → Vitamin A + nutrition ──
  if (types.contains(ClassificationType.persistentDiarrhea) ||
      types.contains(ClassificationType.severePersistentDiarrhea)) {
    final vitA = prescribeVitaminA(ageMonths);
    if (vitA != null && !medicines.any((m) => m.medicineName == 'Vitamin A')) {
      medicines.add(vitA);
    }
  }

  // ── Universal home care ──
  if (!homeCare.contains('Continue breastfeeding')) {
    homeCare.add('Continue breastfeeding and feeding normally');
  }

  // Follow-up schedule
  final followUp = switch (worstSeverity) {
    Severity.red => 'Go to the health facility IMMEDIATELY',
    Severity.yellow => 'Return for follow-up in 2 days',
    Severity.green => 'Return for follow-up in 5 days if not improving',
  };

  return TreatmentPlan(
    medicines: medicines,
    orsGuide: orsGuide,
    preReferralActions: preReferral,
    homeCare: homeCare,
    followUp: followUp,
    returnImmediatelyIf: universalReturnSigns,
    overallSeverity: worstSeverity,
  );
}
