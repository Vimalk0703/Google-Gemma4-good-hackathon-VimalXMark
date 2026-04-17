import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';
import 'home_screen.dart';

/// Splash screen — shows model download progress on first launch.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  double _progress = 0.0;
  String _status = 'Preparing Malaika...';
  bool _isReady = false;

  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    // In a real implementation, this would:
    // 1. Check if model is cached
    // 2. Download if not (2.58GB with progress)
    // 3. Load model into memory
    // 4. Initialize STT/TTS
    //
    // For now, simulate a quick load
    for (var i = 0; i <= 10; i++) {
      await Future.delayed(const Duration(milliseconds: 200));
      if (!mounted) return;
      setState(() {
        _progress = i / 10;
        if (i < 3) {
          _status = 'Checking model cache...';
        } else if (i < 8) {
          _status = 'Loading Gemma 4 E2B...';
        } else {
          _status = 'Almost ready...';
        }
      });
    }

    if (!mounted) return;
    setState(() {
      _isReady = true;
      _status = 'Ready!';
    });

    await Future.delayed(const Duration(milliseconds: 500));
    if (!mounted) return;

    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const HomeScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 48),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Logo
              Text(
                'Malaika',
                style: TextStyle(
                  fontSize: 36,
                  fontWeight: FontWeight.w600,
                  color: MalaikaColors.primary,
                  letterSpacing: 1,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'WHO IMCI Child Health AI',
                style: TextStyle(
                  fontSize: 13,
                  color: MalaikaColors.textMuted,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Powered by Gemma 4 — Fully Offline',
                style: TextStyle(
                  fontSize: 11,
                  color: MalaikaColors.textMuted.withOpacity(0.6),
                ),
              ),

              const SizedBox(height: 48),

              // Progress bar
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: _progress,
                  minHeight: 6,
                  backgroundColor: Colors.white.withOpacity(0.06),
                  valueColor: AlwaysStoppedAnimation(
                    _isReady ? MalaikaColors.green : MalaikaColors.primary,
                  ),
                ),
              ),

              const SizedBox(height: 16),

              // Status text
              Text(
                _status,
                style: TextStyle(
                  fontSize: 13,
                  color: _isReady ? MalaikaColors.green : MalaikaColors.textMuted,
                ),
              ),

              if (!_isReady) ...[
                const SizedBox(height: 8),
                Text(
                  '${(_progress * 100).toInt()}%',
                  style: TextStyle(
                    fontSize: 11,
                    color: MalaikaColors.textMuted.withOpacity(0.5),
                  ),
                ),
              ],

              const SizedBox(height: 48),

              // Offline badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  border: Border.all(color: MalaikaColors.green.withOpacity(0.3)),
                  borderRadius: BorderRadius.circular(20),
                  color: MalaikaColors.green.withOpacity(0.06),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.wifi_off, size: 14, color: MalaikaColors.green),
                    const SizedBox(width: 6),
                    Text(
                      'Works offline after download',
                      style: TextStyle(fontSize: 11, color: MalaikaColors.green),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
