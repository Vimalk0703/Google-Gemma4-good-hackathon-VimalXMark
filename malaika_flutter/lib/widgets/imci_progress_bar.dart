import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';

/// IMCI 5-step progress indicator with icons.
/// Shows completed (green check), active (blue icon), and upcoming (gray) steps.
class ImciProgressBar extends StatelessWidget {
  final int currentStep; // 1-5
  final int totalSteps;

  static const _labels = [
    'Danger\nSigns',
    'Breathing',
    'Diarrhea',
    'Fever',
    'Nutrition',
  ];

  static const _icons = [
    Icons.warning_amber_rounded,
    Icons.air_rounded,
    Icons.water_drop_rounded,
    Icons.thermostat_rounded,
    Icons.restaurant_rounded,
  ];

  const ImciProgressBar({
    super.key,
    required this.currentStep,
    this.totalSteps = 5,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      decoration: const BoxDecoration(
        color: MalaikaColors.surface,
        border: Border(bottom: BorderSide(color: MalaikaColors.border)),
      ),
      child: Row(
        children: List.generate(totalSteps, (i) {
          final stepNum = i + 1;
          final isDone = stepNum < currentStep;
          final isActive = stepNum == currentStep;

          return Expanded(
            child: Row(
              children: [
                if (i > 0)
                  Expanded(
                    child: Container(
                      height: 2,
                      margin: const EdgeInsets.only(bottom: 16),
                      color: isDone
                          ? MalaikaColors.green
                          : isActive
                              ? MalaikaColors.primary.withValues(alpha: 0.3)
                              : MalaikaColors.border,
                    ),
                  ),
                Column(
                  children: [
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      width: isActive ? 36 : 30,
                      height: isActive ? 36 : 30,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isDone
                            ? MalaikaColors.green
                            : isActive
                                ? MalaikaColors.primary
                                : MalaikaColors.surfaceAlt,
                        border: isDone || isActive
                            ? null
                            : Border.all(color: MalaikaColors.border),
                        boxShadow: isActive
                            ? [
                                BoxShadow(
                                  color: MalaikaColors.primary
                                      .withValues(alpha: 0.2),
                                  blurRadius: 8,
                                  spreadRadius: 1,
                                ),
                              ]
                            : null,
                      ),
                      child: Center(
                        child: isDone
                            ? const Icon(Icons.check_rounded,
                                size: 16, color: Colors.white)
                            : Icon(
                                i < _icons.length
                                    ? _icons[i]
                                    : Icons.circle,
                                size: isActive ? 18 : 14,
                                color: isActive
                                    ? Colors.white
                                    : MalaikaColors.textMuted,
                              ),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      i < _labels.length ? _labels[i] : '',
                      style: TextStyle(
                        fontSize: 9,
                        fontWeight:
                            isActive ? FontWeight.w600 : FontWeight.normal,
                        color: isDone
                            ? MalaikaColors.green
                            : isActive
                                ? MalaikaColors.primary
                                : MalaikaColors.textMuted,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
                if (i < totalSteps - 1)
                  Expanded(
                    child: Container(
                      height: 2,
                      margin: const EdgeInsets.only(bottom: 16),
                      color: isDone
                          ? MalaikaColors.green
                          : MalaikaColors.border,
                    ),
                  ),
              ],
            ),
          );
        }),
      ),
    );
  }
}
