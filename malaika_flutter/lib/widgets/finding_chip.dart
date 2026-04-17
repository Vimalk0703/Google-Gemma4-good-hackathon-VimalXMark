import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';

/// Small inline badge showing a detected finding.
class FindingChip extends StatelessWidget {
  final String label;
  final dynamic value; // bool or int or String

  const FindingChip({super.key, required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    final isPositive = value == true;
    final color = isPositive ? MalaikaColors.yellow : MalaikaColors.green;
    final icon = value == true ? '\u2713' : value == false ? '\u2717' : '$value';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.06),
        border: Border.all(color: color.withOpacity(0.15)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        '$label $icon',
        style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: color),
      ),
    );
  }
}
