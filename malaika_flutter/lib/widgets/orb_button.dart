import 'package:flutter/material.dart';
import '../screens/home_screen.dart';
import '../theme/malaika_theme.dart';

/// Animated microphone orb — the primary voice interaction button.
/// Changes appearance based on voice state: idle, listening, thinking, speaking.
class OrbButton extends StatefulWidget {
  final VoiceState state;
  final VoidCallback onTap;

  const OrbButton({super.key, required this.state, required this.onTap});

  @override
  State<OrbButton> createState() => _OrbButtonState();
}

class _OrbButtonState extends State<OrbButton> with TickerProviderStateMixin {
  late final AnimationController _pulseController;
  late final AnimationController _spinController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
    _spinController = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 1500),
    )..repeat();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _spinController.dispose();
    super.dispose();
  }

  Color get _borderColor {
    switch (widget.state) {
      case VoiceState.idle:
        return MalaikaColors.primary.withOpacity(0.25);
      case VoiceState.listening:
        return MalaikaColors.green.withOpacity(0.6);
      case VoiceState.thinking:
        return MalaikaColors.yellow.withOpacity(0.6);
      case VoiceState.speaking:
        return MalaikaColors.primary.withOpacity(0.6);
    }
  }

  Color get _bgColor {
    switch (widget.state) {
      case VoiceState.idle:
        return MalaikaColors.primary.withOpacity(0.08);
      case VoiceState.listening:
        return MalaikaColors.green.withOpacity(0.12);
      case VoiceState.thinking:
        return MalaikaColors.yellow.withOpacity(0.12);
      case VoiceState.speaking:
        return MalaikaColors.primary.withOpacity(0.12);
    }
  }

  IconData get _icon {
    switch (widget.state) {
      case VoiceState.idle:
      case VoiceState.listening:
        return Icons.mic;
      case VoiceState.thinking:
        return Icons.hourglass_top;
      case VoiceState.speaking:
        return Icons.volume_up;
    }
  }

  String get _label {
    switch (widget.state) {
      case VoiceState.idle:
        return 'Tap to talk';
      case VoiceState.listening:
        return 'Listening...';
      case VoiceState.thinking:
        return 'Thinking...';
      case VoiceState.speaking:
        return 'Speaking...';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          onTap: widget.onTap,
          child: AnimatedBuilder(
            listenable: widget.state == VoiceState.speaking
                ? _pulseController
                : widget.state == VoiceState.thinking
                    ? _spinController
                    : _pulseController,
            builder: (context, child) {
              final scale = widget.state == VoiceState.speaking
                  ? 1.0 + _pulseController.value * 0.05
                  : widget.state == VoiceState.listening
                      ? 1.0
                      : 1.0;

              return Transform.scale(
                scale: scale,
                child: Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: _borderColor, width: 2),
                    color: _bgColor,
                  ),
                  child: widget.state == VoiceState.thinking
                      ? RotationTransition(
                          turns: _spinController,
                          child: Icon(_icon, size: 28, color: MalaikaColors.yellow),
                        )
                      : Icon(_icon, size: 28, color: _borderColor),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 4),
        Text(_label, style: TextStyle(fontSize: 11, color: MalaikaColors.textMuted)),
      ],
    );
  }
}

/// Helper — AnimatedBuilder that takes an Animation.
class AnimatedBuilder extends AnimatedWidget {
  final Widget Function(BuildContext, Widget?) builder;

  const AnimatedBuilder({
    super.key,
    required super.listenable,
    required this.builder,
  });

  @override
  Widget build(BuildContext context) => builder(context, null);
}
