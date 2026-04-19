import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';

/// Small inline badge showing a detected clinical finding.
/// Positive findings (yes/number) are amber, negative (no) are green.
/// Auto-filled findings show a sparkle icon.
class FindingChip extends StatelessWidget {
  final String label;
  final dynamic value; // bool or int or String
  final bool isAutoFilled;

  const FindingChip({
    super.key,
    required this.label,
    required this.value,
    this.isAutoFilled = false,
  });

  @override
  Widget build(BuildContext context) {
    final isPositive = value == true;
    final isNumber = value is int && (value as int) > 0;
    final color =
        isPositive || isNumber ? MalaikaColors.yellow : MalaikaColors.green;

    String display;
    if (value == true) {
      display = 'Yes';
    } else if (value == false) {
      display = 'No';
    } else if (value is int) {
      display = '$value';
    } else {
      display = '$value';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        border: Border.all(color: color.withValues(alpha: 0.2)),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isPositive || isNumber
                ? Icons.circle
                : Icons.circle_outlined,
            size: 8,
            color: color,
          ),
          const SizedBox(width: 5),
          Text(
            '$label: $display',
            style: TextStyle(
                fontSize: 11, fontWeight: FontWeight.w500, color: color),
          ),
          if (isAutoFilled) ...[
            const SizedBox(width: 4),
            Icon(Icons.auto_awesome,
                size: 10, color: color.withValues(alpha: 0.7)),
          ],
        ],
      ),
    );
  }
}
