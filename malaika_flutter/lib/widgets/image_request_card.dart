import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';

/// Tappable camera prompt card — asks the caregiver to take a photo.
class ImageRequestCard extends StatelessWidget {
  final String prompt;
  final VoidCallback onTap;

  const ImageRequestCard({super.key, required this.prompt, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: MalaikaColors.primary.withOpacity(0.04),
            border: Border.all(
              color: MalaikaColors.primary.withOpacity(0.25),
              style: BorderStyle.solid,
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            children: [
              Icon(Icons.camera_alt, size: 28, color: MalaikaColors.primary),
              const SizedBox(height: 4),
              Text(
                prompt,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: MalaikaColors.primary,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                'Tap to take a photo',
                style: TextStyle(fontSize: 11, color: MalaikaColors.textMuted),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
