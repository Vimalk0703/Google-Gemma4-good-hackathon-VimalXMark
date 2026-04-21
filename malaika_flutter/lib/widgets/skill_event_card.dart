import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';
import '../core/tool_call_tracker.dart';
import 'finding_chip.dart';

/// Agentic skill event card — shows a tool call invocation with skill name,
/// extracted findings, latency, confidence, and parse method.
///
/// Replaces the old ReasoningCard with an agentic framing that makes
/// Gemma 4's tool-calling architecture visible and auditable.
class SkillEventCard extends StatelessWidget {
  final ToolCallEvent event;
  final List<String> autoFilled;
  final int stepIndex;
  final int totalSteps;

  const SkillEventCard({
    super.key,
    required this.event,
    this.autoFilled = const [],
    this.stepIndex = 0,
    this.totalSteps = 5,
  });

  static const _skillIcons = <String, IconData>{
    'parse_caregiver_response': Icons.psychology_rounded,
    'assess_alertness': Icons.visibility_rounded,
    'assess_skin_color': Icons.palette_rounded,
    'detect_chest_indrawing': Icons.air_rounded,
    'count_breathing_rate': Icons.timer_rounded,
    'classify_breath_sounds': Icons.hearing_rounded,
    'assess_dehydration_signs': Icons.water_drop_rounded,
    'assess_wasting': Icons.monitor_weight_rounded,
    'detect_edema': Icons.back_hand_rounded,
    'classify_imci_step': Icons.verified_rounded,
    'generate_treatment': Icons.medication_rounded,
    'speak_to_caregiver': Icons.record_voice_over_rounded,
  };

  /// User-friendly skill names (not technical identifiers).
  static const _skillDisplayNames = <String, String>{
    'parse_caregiver_response': 'Gemma 4 Processing',
    'assess_alertness': 'Checking Alertness',
    'assess_skin_color': 'Checking Skin Color',
    'detect_chest_indrawing': 'Checking Breathing',
    'count_breathing_rate': 'Counting Breaths',
    'classify_breath_sounds': 'Listening to Breathing',
    'assess_dehydration_signs': 'Checking Dehydration',
    'assess_wasting': 'Checking Nutrition',
    'detect_edema': 'Checking for Swelling',
    'classify_imci_step': 'Health Assessment',
    'generate_treatment': 'Care Recommendations',
    'speak_to_caregiver': 'Responding',
  };

  static const _methodLabels = <String, String>{
    'keyword_match': 'Understanding your response',
    'yes_no_context': 'Understanding your response',
    'gemma4_reasoning': 'Understanding your response',
    'vision_analysis': 'Analyzing photo',
    'deterministic_who': 'WHO health check',
    'gemma4_generation': 'Generating response',
  };

  @override
  Widget build(BuildContext context) {
    final icon = _skillIcons[event.skillName] ?? Icons.build_rounded;
    final isVision = event.inputType == 'image';
    final isDeterministic = event.parseMethod == 'deterministic_who';
    final isLlm = event.parseMethod == 'gemma4_generation';

    // Card accent color based on type
    final accentColor = isDeterministic
        ? MalaikaColors.accent
        : isVision
            ? const Color(0xFF7C3AED) // Purple for vision
            : isLlm
                ? MalaikaColors.primaryDark
                : MalaikaColors.primary;

    final methodLabel =
        _methodLabels[event.parseMethod] ?? event.parseMethod;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: accentColor.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: accentColor.withValues(alpha: 0.15)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header: skill name + badges
            Row(
              children: [
                // Skill icon
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: accentColor.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(icon, size: 15, color: accentColor),
                ),
                const SizedBox(width: 8),
                // Skill name
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _skillDisplayNames[event.skillName] ??
                            _formatSkillName(event.skillName),
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: accentColor,
                          letterSpacing: 0.2,
                        ),
                      ),
                      Text(
                        methodLabel,
                        style: const TextStyle(
                          fontSize: 10,
                          color: MalaikaColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
                // Latency badge
                _LatencyBadge(ms: event.durationMs, color: accentColor),
                const SizedBox(width: 6),
                // Step badge
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                  decoration: BoxDecoration(
                    color: accentColor.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '$stepIndex/$totalSteps',
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w600,
                      color: accentColor,
                    ),
                  ),
                ),
              ],
            ),

            // Findings chips
            if (event.findings.isNotEmpty) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: event.findings.entries.map((e) {
                  return FindingChip(
                    label: _formatLabel(e.key),
                    value: e.value,
                    isAutoFilled: autoFilled.contains(e.key),
                  );
                }).toList(),
              ),
            ],

            // Bottom row: confidence + auto-fill notice
            const SizedBox(height: 8),
            Row(
              children: [
                // Success indicator
                Icon(
                  event.success
                      ? Icons.check_circle_rounded
                      : Icons.error_rounded,
                  size: 12,
                  color: event.success
                      ? MalaikaColors.green
                      : MalaikaColors.red,
                ),
                const SizedBox(width: 4),
                Text(
                  '${(event.confidence * 100).round()}% confidence',
                  style: const TextStyle(
                    fontSize: 10,
                    color: MalaikaColors.textMuted,
                  ),
                ),
                if (autoFilled.isNotEmpty) ...[
                  const SizedBox(width: 10),
                  const Icon(Icons.auto_awesome,
                      size: 11, color: MalaikaColors.accent),
                  const SizedBox(width: 3),
                  Text(
                    '${autoFilled.length} auto-detected',
                    style: const TextStyle(
                        fontSize: 10, color: MalaikaColors.accent),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  static String _formatSkillName(String name) {
    return name
        .replaceAll('_', ' ')
        .split(' ')
        .map((w) =>
            w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');
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

/// Latency badge — color-coded by speed.
class _LatencyBadge extends StatelessWidget {
  final int ms;
  final Color color;
  const _LatencyBadge({required this.ms, required this.color});

  @override
  Widget build(BuildContext context) {
    final label = ms < 1000 ? '${ms}ms' : '${(ms / 1000).toStringAsFixed(1)}s';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.timer_outlined, size: 10, color: color),
          const SizedBox(width: 3),
          Text(
            label,
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}
