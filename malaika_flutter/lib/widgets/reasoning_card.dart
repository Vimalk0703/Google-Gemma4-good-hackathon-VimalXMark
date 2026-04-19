import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';
import 'finding_chip.dart';

/// Reasoning transparency card — shows what the AI extracted from the user's
/// response. Appears inline in the chat between user message and bot response.
///
/// This is the key differentiator: makes the AI's clinical reasoning visible
/// and auditable. Shows extracted findings, auto-fills, and current protocol step.
class ReasoningCard extends StatelessWidget {
  final Map<String, dynamic> findings;
  final List<String> autoFilled;
  final String stepName;
  final int stepIndex;
  final int totalSteps;

  const ReasoningCard({
    super.key,
    required this.findings,
    this.autoFilled = const [],
    required this.stepName,
    required this.stepIndex,
    this.totalSteps = 5,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: MalaikaColors.primaryLight.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
              color: MalaikaColors.primary.withValues(alpha: 0.12)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                const Icon(Icons.psychology_rounded,
                    size: 16, color: MalaikaColors.primary),
                const SizedBox(width: 6),
                const Text(
                  'Gemma Processing',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: MalaikaColors.primary,
                  ),
                ),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: MalaikaColors.primary.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    'Step $stepIndex/$totalSteps',
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: MalaikaColors.primary,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            // Findings chips
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: findings.entries.map((e) {
                return FindingChip(
                  label: _formatLabel(e.key),
                  value: e.value,
                  isAutoFilled: autoFilled.contains(e.key),
                );
              }).toList(),
            ),
            // Auto-fill notice
            if (autoFilled.isNotEmpty) ...[
              const SizedBox(height: 8),
              Row(
                children: [
                  const Icon(Icons.auto_awesome,
                      size: 12, color: MalaikaColors.accent),
                  const SizedBox(width: 4),
                  Text(
                    '${autoFilled.length} finding${autoFilled.length > 1 ? "s" : ""} auto-detected from your response',
                    style: const TextStyle(
                        fontSize: 11, color: MalaikaColors.accent),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  static String _formatLabel(String key) {
    return key
        .replaceAll('_', ' ')
        .split(' ')
        .map((w) =>
            w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');
  }
}
