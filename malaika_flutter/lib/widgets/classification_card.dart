import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';

/// WHO IMCI classification card — RED/YELLOW/GREEN severity.
class ClassificationCard extends StatelessWidget {
  final String step;
  final String severity;
  final String label;
  final String reasoning;

  const ClassificationCard({
    super.key,
    required this.step,
    required this.severity,
    required this.label,
    required this.reasoning,
  });

  @override
  Widget build(BuildContext context) {
    final color = MalaikaColors.forSeverity(severity);
    final bgColor = MalaikaColors.forSeverityBackground(severity);
    final badgeLabel = MalaikaColors.severityLabel(severity);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: bgColor,
          border: Border.all(color: color.withOpacity(0.25)),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: step name + badge
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  step.replaceAll('_', ' ').split(' ').map((w) =>
                    w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : w
                  ).join(' '),
                  style: TextStyle(fontSize: 11, color: MalaikaColors.textMuted),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(
                    color: color.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(5),
                  ),
                  child: Text(
                    badgeLabel,
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: color,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            // Classification label
            Text(
              label,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: MalaikaColors.text,
              ),
            ),
            const SizedBox(height: 2),
            // Reasoning
            Text(
              reasoning,
              style: TextStyle(
                fontSize: 11,
                color: MalaikaColors.textMuted,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 3),
            // Source
            Text(
              'WHO IMCI Classification',
              style: TextStyle(
                fontSize: 9,
                color: MalaikaColors.textMuted.withOpacity(0.5),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
