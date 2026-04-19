import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';

/// Emergency Signs — static WHO reference for when to seek immediate help.
/// Genuinely useful offline content from WHO IMCI protocol.
class EmergencySignsScreen extends StatelessWidget {
  const EmergencySignsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Emergency Signs',
            style: TextStyle(fontWeight: FontWeight.w600)),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // Critical alert
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: MalaikaColors.redLight,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                  color: MalaikaColors.red.withValues(alpha: 0.3)),
            ),
            child: const Row(
              children: [
                Icon(Icons.warning_rounded,
                    size: 24, color: MalaikaColors.red),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Take your child to a health facility IMMEDIATELY if you see ANY of these signs.',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: MalaikaColors.red,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Danger signs
          _buildSection(
            'General Danger Signs',
            Icons.warning_amber_rounded,
            MalaikaColors.red,
            [
              _Sign(
                'Unable to drink or breastfeed',
                'Child refuses all fluids or is too weak to swallow.',
              ),
              _Sign(
                'Vomits everything',
                'Cannot keep down any food or liquid.',
              ),
              _Sign(
                'Convulsions or seizures',
                'Uncontrolled shaking, jerking, or stiffening of the body.',
              ),
              _Sign(
                'Abnormally sleepy or unconscious',
                'Cannot be woken or does not respond when spoken to.',
              ),
            ],
          ),
          const SizedBox(height: 16),

          _buildSection(
            'Breathing Emergency',
            Icons.air_rounded,
            MalaikaColors.red,
            [
              _Sign(
                'Severe chest indrawing',
                'Lower chest pulls inward when child breathes in. Sign of severe pneumonia.',
              ),
              _Sign(
                'Stridor when calm',
                'Harsh breathing noise when the child is NOT crying.',
              ),
            ],
          ),
          const SizedBox(height: 16),

          _buildSection(
            'Severe Dehydration',
            Icons.water_drop_rounded,
            MalaikaColors.red,
            [
              _Sign(
                'Sunken eyes + skin pinch very slow',
                'Skin takes more than 2 seconds to go back when pinched.',
              ),
              _Sign(
                'Unable to drink or drinking poorly',
                'Combined with diarrhea — severe fluid loss.',
              ),
            ],
          ),
          const SizedBox(height: 16),

          _buildSection(
            'Fever Emergency',
            Icons.thermostat_rounded,
            MalaikaColors.red,
            [
              _Sign(
                'Stiff neck with fever',
                'Cannot bend neck forward. Possible meningitis.',
              ),
              _Sign(
                'Fever with lethargy',
                'Very high fever with child unable to wake or respond.',
              ),
            ],
          ),
          const SizedBox(height: 16),

          _buildSection(
            'Severe Malnutrition',
            Icons.restaurant_rounded,
            MalaikaColors.red,
            [
              _Sign(
                'Visible severe wasting',
                'Child is extremely thin with ribs and bones clearly visible.',
              ),
              _Sign(
                'Swelling of both feet',
                'Bilateral edema — press on top of foot and it leaves a dent.',
              ),
            ],
          ),
          const SizedBox(height: 24),

          // When to return
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: MalaikaColors.yellowLight,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                  color: MalaikaColors.yellow.withValues(alpha: 0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.info_rounded,
                        size: 20, color: MalaikaColors.yellow),
                    SizedBox(width: 8),
                    Text('Return Sooner If...',
                        style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w600,
                            color: MalaikaColors.yellow)),
                  ],
                ),
                const SizedBox(height: 10),
                ...[
                  'Child is not able to drink or breastfeed',
                  'Child becomes sicker',
                  'Child develops a fever',
                  'Blood in stool appears',
                  'Child is drinking poorly',
                ].map((text) => Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Padding(
                            padding: EdgeInsets.only(top: 6),
                            child: Icon(Icons.circle, size: 5,
                                color: MalaikaColors.yellow),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(text,
                                style: const TextStyle(
                                    fontSize: 13,
                                    color: MalaikaColors.textSecondary,
                                    height: 1.4)),
                          ),
                        ],
                      ),
                    )),
              ],
            ),
          ),
          const SizedBox(height: 20),

          // Source
          const Center(
            child: Text(
              'Source: WHO IMCI Chart Booklet (2014, reaffirmed 2023)',
              style: TextStyle(fontSize: 11, color: MalaikaColors.textMuted),
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildSection(
      String title, IconData icon, Color color, List<_Sign> signs) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: MalaikaColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: MalaikaColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 20, color: color),
              const SizedBox(width: 8),
              Text(title,
                  style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: MalaikaColors.text)),
            ],
          ),
          const SizedBox(height: 12),
          ...signs.map((s) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(s.title,
                        style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: MalaikaColors.text)),
                    const SizedBox(height: 2),
                    Text(s.desc,
                        style: const TextStyle(
                            fontSize: 12,
                            color: MalaikaColors.textSecondary,
                            height: 1.4)),
                  ],
                ),
              )),
        ],
      ),
    );
  }
}

class _Sign {
  final String title;
  final String desc;
  const _Sign(this.title, this.desc);
}
