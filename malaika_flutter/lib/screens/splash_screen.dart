import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';
import '../inference/model_manager.dart';
import '../inference/gemma_inference_service.dart';
import 'home_screen.dart';

/// Splash screen — downloads model on first launch, then loads it.
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  double _progress = 0.0;
  String _status = 'Checking for model...';
  bool _isReady = false;
  bool _hasError = false;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    try {
      // Check if model is cached
      final isCached = await ModelManager.isModelCached();

      if (isCached) {
        setState(() => _status = 'Model found. Loading...');
        setState(() => _progress = 0.5);
      } else {
        // Download model
        setState(() => _status = 'Downloading Gemma 4 E2B (one-time, ~1.8 GB)...');

        await ModelManager.downloadModel(
          onProgress: (p) {
            if (mounted) setState(() {
              _progress = p * 0.8; // 80% for download
              _status = 'Downloading... ${(p * 100).toInt()}%';
            });
          },
        );
      }

      // Load model
      setState(() {
        _progress = 0.9;
        _status = 'Loading model into memory...';
      });

      final modelPath = await ModelManager.modelPath;
      final inference = GemmaInferenceService();
      await inference.loadModel(modelPath);

      setState(() {
        _progress = 1.0;
        _isReady = true;
        _status = 'Ready!';
      });

      await Future.delayed(const Duration(milliseconds: 500));
      if (!mounted) return;

      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => HomeScreen(inference: inference),
        ),
      );
    } catch (e) {
      setState(() {
        _hasError = true;
        _errorMessage = e.toString();
        _status = 'Error loading model';
      });
    }
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
              const Text(
                'Malaika',
                style: TextStyle(
                  fontSize: 36,
                  fontWeight: FontWeight.w600,
                  color: MalaikaColors.primary,
                  letterSpacing: 1,
                ),
              ),
              const SizedBox(height: 4),
              const Text(
                'WHO IMCI Child Health AI',
                style: TextStyle(fontSize: 13, color: MalaikaColors.textMuted),
              ),
              const SizedBox(height: 8),
              Text(
                'Powered by Gemma 4 — Fully Offline',
                style: TextStyle(
                  fontSize: 11,
                  color: MalaikaColors.textMuted.withValues(alpha: 0.6),
                ),
              ),
              const SizedBox(height: 48),

              // Progress bar
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: _progress,
                  minHeight: 6,
                  backgroundColor: Colors.white.withValues(alpha: 0.06),
                  valueColor: AlwaysStoppedAnimation(
                    _hasError
                        ? MalaikaColors.red
                        : _isReady
                            ? MalaikaColors.green
                            : MalaikaColors.primary,
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Status
              Text(
                _status,
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 13,
                  color: _hasError
                      ? MalaikaColors.red
                      : _isReady
                          ? MalaikaColors.green
                          : MalaikaColors.textMuted,
                ),
              ),

              if (_hasError) ...[
                const SizedBox(height: 8),
                Text(
                  _errorMessage,
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 10, color: MalaikaColors.red.withValues(alpha: 0.7)),
                ),
                const SizedBox(height: 16),
                // Skip button — run without model (demo mode)
                TextButton(
                  onPressed: () {
                    Navigator.of(context).pushReplacement(
                      MaterialPageRoute(
                        builder: (_) => const HomeScreen(),
                      ),
                    );
                  },
                  child: const Text('Continue without model (demo mode)'),
                ),
              ],

              if (!_hasError && !_isReady) ...[
                const SizedBox(height: 8),
                Text(
                  '${(_progress * 100).toInt()}%',
                  style: TextStyle(
                    fontSize: 11,
                    color: MalaikaColors.textMuted.withValues(alpha: 0.5),
                  ),
                ),
              ],

              const SizedBox(height: 48),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  border: Border.all(color: MalaikaColors.green.withValues(alpha: 0.3)),
                  borderRadius: BorderRadius.circular(20),
                  color: MalaikaColors.green.withValues(alpha: 0.06),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.wifi_off, size: 14, color: MalaikaColors.green),
                    SizedBox(width: 6),
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
