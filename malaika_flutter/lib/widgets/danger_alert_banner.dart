import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';

/// Pulsing red danger alert banner for urgent referral.
class DangerAlertBanner extends StatefulWidget {
  final String message;

  const DangerAlertBanner({super.key, required this.message});

  @override
  State<DangerAlertBanner> createState() => _DangerAlertBannerState();
}

class _DangerAlertBannerState extends State<DangerAlertBanner>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: MalaikaColors.red.withOpacity(0.1),
              border: Border.all(
                color: MalaikaColors.red,
                width: 2,
              ),
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: MalaikaColors.red.withOpacity(0.25 * _controller.value),
                  blurRadius: 8,
                  spreadRadius: 0,
                ),
              ],
            ),
            child: Row(
              children: [
                const Text('\u26A0', style: TextStyle(fontSize: 20)),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    widget.message,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: MalaikaColors.red,
                      height: 1.3,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

/// AnimatedBuilder helper.
class AnimatedBuilder extends AnimatedWidget {
  final Widget Function(BuildContext, Widget?) builder;
  const AnimatedBuilder({super.key, required super.listenable, required this.builder});
  @override
  Widget build(BuildContext context) => builder(context, null);
}
