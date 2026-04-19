import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';
import 'home_screen.dart';
import 'emergency_signs_screen.dart';

/// Dashboard — the app home screen.
///
/// Shows the main IMCI assessment action, quick reference features,
/// and technology info. Multiple functionalities, not just a chat.
class DashboardScreen extends StatelessWidget {
  final bool modelLoaded;
  const DashboardScreen({super.key, required this.modelLoaded});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 40),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(),
              const SizedBox(height: 28),
              _buildHeroCard(context),
              const SizedBox(height: 28),
              _buildSectionTitle('How It Works'),
              const SizedBox(height: 12),
              _buildHowItWorks(),
              const SizedBox(height: 28),
              _buildSectionTitle('Quick Reference'),
              const SizedBox(height: 12),
              _buildQuickRefGrid(context),
              const SizedBox(height: 28),
              _buildTechFooter(),
            ],
          ),
        ),
      ),
    );
  }

  // --------------------------------------------------------------------------
  // Header
  // --------------------------------------------------------------------------

  Widget _buildHeader() {
    return Row(
      children: [
        Container(
          width: 44,
          height: 44,
          decoration: BoxDecoration(
            color: MalaikaColors.primaryLight,
            borderRadius: BorderRadius.circular(14),
          ),
          child: const Icon(Icons.favorite_rounded,
              size: 22, color: MalaikaColors.primary),
        ),
        const SizedBox(width: 12),
        const Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Malaika',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: MalaikaColors.text,
                  letterSpacing: -0.5,
                ),
              ),
              Text(
                'WHO Child Health AI',
                style: TextStyle(
                  fontSize: 13,
                  color: MalaikaColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        // Offline badge
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: MalaikaColors.greenLight,
            borderRadius: BorderRadius.circular(20),
            border:
                Border.all(color: MalaikaColors.green.withValues(alpha: 0.2)),
          ),
          child: const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.wifi_off_rounded,
                  size: 13, color: MalaikaColors.green),
              SizedBox(width: 5),
              Text(
                'Offline',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: MalaikaColors.green,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // --------------------------------------------------------------------------
  // Hero Card — Start Assessment
  // --------------------------------------------------------------------------

  Widget _buildHeroCard(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [MalaikaColors.primary, Color(0xFF0091EA)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: MalaikaColors.primary.withValues(alpha: 0.25),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Icon(Icons.health_and_safety_rounded,
                size: 24, color: Colors.white),
          ),
          const SizedBox(height: 16),
          const Text(
            'IMCI Assessment',
            style: TextStyle(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: Colors.white,
              letterSpacing: -0.3,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            'Check your child\'s health using the WHO Integrated '
            'Management of Childhood Illness protocol.',
            style: TextStyle(
              fontSize: 14,
              color: Colors.white.withValues(alpha: 0.85),
              height: 1.5,
            ),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                    builder: (_) =>
                        HomeScreen(modelLoaded: modelLoaded)),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.white,
                foregroundColor: MalaikaColors.primary,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12)),
                elevation: 0,
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text('Start Assessment',
                      style: TextStyle(
                          fontWeight: FontWeight.w600, fontSize: 15)),
                  SizedBox(width: 8),
                  Icon(Icons.arrow_forward_rounded, size: 18),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // --------------------------------------------------------------------------
  // How It Works
  // --------------------------------------------------------------------------

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: const TextStyle(
        fontSize: 17,
        fontWeight: FontWeight.w600,
        color: MalaikaColors.text,
      ),
    );
  }

  Widget _buildHowItWorks() {
    const steps = [
      _HowStep(
        icon: Icons.chat_bubble_outline_rounded,
        title: 'Answer Questions',
        desc: 'Tell Malaika about your child\'s symptoms through a simple conversation.',
      ),
      _HowStep(
        icon: Icons.psychology_rounded,
        title: 'AI Analysis',
        desc: 'Gemma 4 processes responses and extracts clinical findings on-device.',
      ),
      _HowStep(
        icon: Icons.assignment_turned_in_rounded,
        title: 'WHO Classification',
        desc: 'Deterministic WHO IMCI protocol classifies severity for each area.',
      ),
      _HowStep(
        icon: Icons.local_hospital_rounded,
        title: 'Care Guidance',
        desc: 'Get clear, actionable guidance on next steps for your child\'s health.',
      ),
    ];

    return Column(
      children: [
        for (var i = 0; i < steps.length; i++) ...[
          _buildStep(i + 1, steps[i]),
          if (i < steps.length - 1) const SizedBox(height: 10),
        ],
      ],
    );
  }

  Widget _buildStep(int number, _HowStep step) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: MalaikaColors.surface,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: MalaikaColors.border),
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: MalaikaColors.primaryLight,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Center(
              child: Text(
                '$number',
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  color: MalaikaColors.primary,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(step.title,
                    style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: MalaikaColors.text)),
                const SizedBox(height: 2),
                Text(step.desc,
                    style: const TextStyle(
                        fontSize: 12,
                        color: MalaikaColors.textSecondary,
                        height: 1.4)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // --------------------------------------------------------------------------
  // Quick Reference Grid
  // --------------------------------------------------------------------------

  Widget _buildQuickRefGrid(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _buildFeatureCard(
            icon: Icons.warning_amber_rounded,
            iconColor: MalaikaColors.red,
            iconBg: MalaikaColors.redLight,
            title: 'Emergency Signs',
            subtitle: 'When to seek help',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute(
                  builder: (_) => const EmergencySignsScreen()),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _buildFeatureCard(
            icon: Icons.menu_book_rounded,
            iconColor: MalaikaColors.primary,
            iconBg: MalaikaColors.primaryLight,
            title: 'IMCI Guide',
            subtitle: 'Protocol reference',
            onTap: () => _showAbout(context),
          ),
        ),
      ],
    );
  }

  Widget _buildFeatureCard({
    required IconData icon,
    required Color iconColor,
    required Color iconBg,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: MalaikaColors.surface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: MalaikaColors.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: iconBg,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, size: 20, color: iconColor),
            ),
            const SizedBox(height: 12),
            Text(title,
                style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: MalaikaColors.text)),
            const SizedBox(height: 2),
            Text(subtitle,
                style: const TextStyle(
                    fontSize: 12, color: MalaikaColors.textSecondary)),
          ],
        ),
      ),
    );
  }

  void _showAbout(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: MalaikaColors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => DraggableScrollableSheet(
        initialChildSize: 0.6,
        minChildSize: 0.3,
        maxChildSize: 0.85,
        expand: false,
        builder: (_, controller) => ListView(
          controller: controller,
          padding: const EdgeInsets.all(24),
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: MalaikaColors.border,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 20),
            const Text('WHO IMCI Protocol',
                style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w700,
                    color: MalaikaColors.text)),
            const SizedBox(height: 12),
            const Text(
              'The Integrated Management of Childhood Illness (IMCI) is '
              'a WHO strategy for reducing child mortality. It provides a '
              'systematic approach to assessing and treating the most '
              'common causes of childhood illness.',
              style: TextStyle(
                  fontSize: 14,
                  color: MalaikaColors.textSecondary,
                  height: 1.6),
            ),
            const SizedBox(height: 20),
            _aboutSection('Assessment Areas', [
              'General Danger Signs — consciousness, drinking, vomiting, convulsions',
              'Cough & Breathing — pneumonia detection',
              'Diarrhea & Dehydration — fluid loss assessment',
              'Fever — malaria, meningitis, measles screening',
              'Nutrition — malnutrition and growth',
            ]),
            const SizedBox(height: 16),
            _aboutSection('Classification System', [
              'RED — Urgent referral to hospital immediately',
              'YELLOW — Specific treatment, follow up in 24 hours',
              'GREEN — Home management with follow-up in 5 days',
            ]),
            const SizedBox(height: 16),
            _aboutSection('Important', [
              'This app is a decision SUPPORT tool, not a diagnosis',
              'Always consult a qualified health worker',
              'Based on WHO IMCI Chart Booklet (2014, reaffirmed 2023)',
            ]),
          ],
        ),
      ),
    );
  }

  Widget _aboutSection(String title, List<String> items) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title,
            style: const TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: MalaikaColors.text)),
        const SizedBox(height: 8),
        ...items.map((item) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.only(top: 6),
                    child: Icon(Icons.circle, size: 5,
                        color: MalaikaColors.textMuted),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(item,
                        style: const TextStyle(
                            fontSize: 13,
                            color: MalaikaColors.textSecondary,
                            height: 1.5)),
                  ),
                ],
              ),
            )),
      ],
    );
  }

  // --------------------------------------------------------------------------
  // Tech Footer
  // --------------------------------------------------------------------------

  Widget _buildTechFooter() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: MalaikaColors.surfaceAlt,
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: MalaikaColors.surface,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: MalaikaColors.border),
            ),
            child: const Icon(Icons.memory_rounded,
                size: 20, color: MalaikaColors.primary),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Powered by Google Gemma 4',
                    style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: MalaikaColors.text)),
                Text(
                  'On-device AI. No internet needed. Your data stays private.',
                  style: TextStyle(
                      fontSize: 11,
                      color: MalaikaColors.textSecondary,
                      height: 1.4),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _HowStep {
  final IconData icon;
  final String title;
  final String desc;
  const _HowStep(
      {required this.icon, required this.title, required this.desc});
}
