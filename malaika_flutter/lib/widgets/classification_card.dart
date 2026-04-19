import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';

/// WHO IMCI classification card — RED/YELLOW/GREEN severity.
/// Enhanced with icon, better layout, and WHO protocol attribution.
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
    final icon = MalaikaColors.severityIcon(severity);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: bgColor,
          border: Border.all(color: color.withValues(alpha: 0.3)),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: icon + step + severity badge
            Row(
              children: [
                Icon(icon, size: 20, color: color),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    step,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: MalaikaColors.textSecondary,
                    ),
                  ),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20),
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
            const SizedBox(height: 10),
            // Classification label
            Text(
              label,
              style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: MalaikaColors.text,
              ),
            ),
            const SizedBox(height: 4),
            // Reasoning
            Text(
              reasoning,
              style: const TextStyle(
                fontSize: 13,
                color: MalaikaColors.textSecondary,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 10),
            // WHO attribution
            Row(
              children: [
                Icon(Icons.verified_rounded,
                    size: 12, color: MalaikaColors.textMuted),
                const SizedBox(width: 4),
                Text(
                  'WHO IMCI Protocol',
                  style: TextStyle(
                    fontSize: 11,
                    color: MalaikaColors.textMuted,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
