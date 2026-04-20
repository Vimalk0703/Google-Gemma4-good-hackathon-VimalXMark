import 'dart:math';
import 'package:flutter/material.dart';
import '../screens/home_screen.dart';
import '../theme/malaika_theme.dart';

/// Animated audio waveform — shows frequency bars during listening/speaking.
class VoiceWaveform extends StatefulWidget {
  final VoiceState state;
  const VoiceWaveform({super.key, required this.state});

  @override
  State<VoiceWaveform> createState() => _VoiceWaveformState();
}

class _VoiceWaveformState extends State<VoiceWaveform>
    with TickerProviderStateMixin {
  late final List<AnimationController> _controllers;
  late final List<Animation<double>> _animations;
  final _random = Random();
  static const _barCount = 24;

  @override
  void initState() {
    super.initState();
    _controllers = List.generate(_barCount, (i) {
      return AnimationController(
        vsync: this,
        duration: Duration(milliseconds: 300 + _random.nextInt(400)),
      );
    });
    _animations = _controllers.map((c) {
      return Tween<double>(begin: 0.08, end: 0.3 + _random.nextDouble() * 0.7)
          .animate(CurvedAnimation(parent: c, curve: Curves.easeInOut));
    }).toList();
    _updateAnimations();
  }

  @override
  void didUpdateWidget(VoiceWaveform old) {
    super.didUpdateWidget(old);
    if (old.state != widget.state) _updateAnimations();
  }

  void _updateAnimations() {
    final active =
        widget.state == VoiceState.listening ||
        widget.state == VoiceState.speaking;

    for (int i = 0; i < _barCount; i++) {
      if (active) {
        // Stagger start for organic feel
        Future.delayed(Duration(milliseconds: i * 30), () {
          if (mounted && _isActive) {
            _controllers[i].repeat(reverse: true);
          }
        });
      } else {
        _controllers[i].animateTo(0.08,
            duration: const Duration(milliseconds: 300));
      }
    }
  }

  bool get _isActive =>
      widget.state == VoiceState.listening ||
      widget.state == VoiceState.speaking;

  Color get _barColor {
    switch (widget.state) {
      case VoiceState.listening:
        return MalaikaColors.green;
      case VoiceState.speaking:
        return MalaikaColors.primary;
      case VoiceState.thinking:
        return MalaikaColors.yellow;
      case VoiceState.idle:
        return MalaikaColors.textMuted;
    }
  }

  String get _label {
    switch (widget.state) {
      case VoiceState.listening:
        return 'Listening...';
      case VoiceState.speaking:
        return 'Speaking...';
      case VoiceState.thinking:
        return 'Thinking...';
      case VoiceState.idle:
        return 'Voice mode';
    }
  }

  @override
  void dispose() {
    for (final c in _controllers) {
      c.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          height: 40,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: List.generate(_barCount, (i) {
              return _AnimatedBuilder(
                animation: _animations[i],
                builder: (context, _) {
                  return Container(
                    width: 3,
                    height: 40 * _animations[i].value,
                    margin: const EdgeInsets.symmetric(horizontal: 1.5),
                    decoration: BoxDecoration(
                      color: _barColor.withOpacity(
                          _isActive ? 0.7 + 0.3 * _animations[i].value : 0.3),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  );
                },
              );
            }),
          ),
        ),
        const SizedBox(height: 4),
        Text(
          _label,
          style: TextStyle(
            fontSize: 11,
            color: _barColor,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

/// _AnimatedBuilder helper.
class _AnimatedBuilder extends AnimatedWidget {
  final Widget Function(BuildContext, Widget?) builder;

  const _AnimatedBuilder({
    super.key,
    required Animation<double> animation,
    required this.builder,
  }) : super(listenable: animation);

  @override
  Widget build(BuildContext context) => builder(context, null);
}
