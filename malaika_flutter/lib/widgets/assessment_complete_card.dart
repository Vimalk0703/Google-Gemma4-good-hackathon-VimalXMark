import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';

/// Final assessment summary card with all domain classifications.
class AssessmentCompleteCard extends StatelessWidget {
  final String severity;
  final String urgency;
  final List<Map<String, String>> classifications;

  const AssessmentCompleteCard({
    super.key,
    required this.severity,
    required this.urgency,
    required this.classifications,
  });

  @override
  Widget build(BuildContext context) {
    final color = MalaikaColors.forSeverity(severity);
    final bgColor = MalaikaColors.forSeverityBackground(severity);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: bgColor,
          border: Border.all(color: color.withOpacity(0.25)),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          children: [
            // Header
            Text(
              'Assessment Complete',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: color),
            ),
            const SizedBox(height: 2),
            Text(urgency, style: TextStyle(fontSize: 12, color: MalaikaColors.textMuted)),
            const SizedBox(height: 8),

            // Classifications list
            ...classifications.map((c) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    c['domain'] ?? '',
                    style: TextStyle(fontSize: 12, color: MalaikaColors.text),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                    decoration: BoxDecoration(
                      color: MalaikaColors.forSeverity(c['severity'] ?? 'green').withOpacity(0.15),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      c['classification'] ?? '',
                      style: TextStyle(
                        fontSize: 9,
                        fontWeight: FontWeight.w700,
                        color: MalaikaColors.forSeverity(c['severity'] ?? 'green'),
                      ),
                    ),
                  ),
                ],
              ),
            )),

            const SizedBox(height: 6),
            Text(
              'Based on WHO IMCI Chart Booklet classifications',
              style: TextStyle(fontSize: 9, color: MalaikaColors.textMuted.withOpacity(0.5)),
            ),
          ],
        ),
      ),
    );
  }
}
