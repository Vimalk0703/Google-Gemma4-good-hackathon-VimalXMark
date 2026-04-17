import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';

/// Skill execution card — shows spinner while processing, checkmark when done.
class SkillCard extends StatelessWidget {
  final String skillName;
  final String description;
  final bool isDone;

  const SkillCard({
    super.key,
    required this.skillName,
    required this.description,
    this.isDone = false,
  });

  @override
  Widget build(BuildContext context) {
    final color = isDone ? MalaikaColors.green : MalaikaColors.primary;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: color.withOpacity(0.04),
          border: Border.all(color: color.withOpacity(0.2)),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          children: [
            // Icon: spinner or checkmark
            if (isDone)
              Icon(Icons.check_circle, size: 16, color: MalaikaColors.green)
            else
              SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation(MalaikaColors.primary),
                ),
              ),
            const SizedBox(width: 8),
            // Text
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isDone
                        ? skillName.replaceAll('_', ' ').split(' ').map((w) =>
                            w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : w
                          ).join(' ')
                        : description,
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: color,
                    ),
                  ),
                  if (isDone && description.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(
                        description,
                        style: TextStyle(fontSize: 10, color: MalaikaColors.textMuted, height: 1.4),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
