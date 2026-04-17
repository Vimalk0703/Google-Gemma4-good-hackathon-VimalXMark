import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';

/// IMCI 5-step progress indicator.
class ImciProgressBar extends StatelessWidget {
  final int currentStep; // 1-5
  final int totalSteps;

  static const _labels = ['Danger Signs', 'Breathing', 'Diarrhea', 'Fever', 'Nutrition'];

  const ImciProgressBar({
    super.key,
    required this.currentStep,
    this.totalSteps = 5,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
      child: Row(
        children: List.generate(totalSteps, (i) {
          final stepNum = i + 1;
          final isDone = stepNum < currentStep;
          final isActive = stepNum == currentStep;

          return Expanded(
            child: Column(
              children: [
                // Connector line + dot
                Row(
                  children: [
                    // Left connector
                    if (i > 0)
                      Expanded(
                        child: Container(
                          height: 2,
                          color: isDone || isActive
                              ? MalaikaColors.green
                              : Colors.white.withOpacity(0.06),
                        ),
                      ),
                    // Dot
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      width: isActive ? 28 : 24,
                      height: isActive ? 28 : 24,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isDone
                            ? MalaikaColors.green
                            : isActive
                                ? MalaikaColors.primary
                                : Colors.white.withOpacity(0.1),
                      ),
                      child: Center(
                        child: Text(
                          '$stepNum',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: isDone || isActive
                                ? MalaikaColors.background
                                : MalaikaColors.textMuted,
                          ),
                        ),
                      ),
                    ),
                    // Right connector
                    if (i < totalSteps - 1)
                      Expanded(
                        child: Container(
                          height: 2,
                          color: isDone
                              ? MalaikaColors.green
                              : Colors.white.withOpacity(0.06),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 2),
                // Label
                Text(
                  i < _labels.length ? _labels[i] : '',
                  style: TextStyle(
                    fontSize: 8,
                    color: isActive ? MalaikaColors.primary : MalaikaColors.textMuted,
                    fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
                  ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          );
        }),
      ),
    );
  }
}
