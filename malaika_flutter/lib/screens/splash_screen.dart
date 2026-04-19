import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_gemma/flutter_gemma.dart';
import 'package:path_provider/path_provider.dart';
import '../theme/malaika_theme.dart';
import 'dashboard_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  double _progress = 0.0;
  String _status = 'Initializing...';
  bool _isReady = false;
  bool _hasError = false;
  String _errorMessage = '';

  /// Expected model file size in bytes (~2.58 GB).
  static const _expectedModelSize = 2580000000;

  /// Timer for polling download file size.
  Timer? _progressTimer;

  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  @override
  void dispose() {
    _progressTimer?.cancel();
    super.dispose();
  }

  Future<void> _initializeApp() async {
    try {
      setState(() => _status = 'Initializing Gemma framework...');
      await FlutterGemma.initialize(
        huggingFaceToken:
            const String.fromEnvironment('HF_TOKEN', defaultValue: ''),
      );
      setState(() => _progress = 0.05);

      final appDir = await getApplicationDocumentsDirectory();
      final modelPath = '${appDir.path}/gemma-4-E2B-it.litertlm';
      final modelFile = File(modelPath);
      final alreadyCached =
          await modelFile.exists() &&
          await modelFile.length() > 1000000000;

      if (alreadyCached) {
        setState(() {
          _status = 'Model found locally';
          _progress = 0.8;
        });
      } else {
        setState(() => _status = 'Downloading Gemma 4 E2B (2.6 GB)...');
        _startProgressPolling(modelPath);
      }

      await FlutterGemma.installModel(
        modelType: ModelType.gemmaIt,
        fileType: ModelFileType.litertlm,
      )
          .fromNetwork(
            'https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm/resolve/main/gemma-4-E2B-it.litertlm',
            token: const String.fromEnvironment('HF_TOKEN',
                defaultValue: ''),
          )
          .withProgress((progress) {
            if (mounted) {
              final pct = progress > 1.0 ? progress : progress * 100;
              final clamped = pct.clamp(0.0, 100.0);
              setState(() {
                _progress = 0.05 + (clamped / 100.0) * 0.75;
                _status =
                    'Downloading... ${clamped.toInt()}% of 2.6 GB';
              });
            }
          })
          .install();

      _progressTimer?.cancel();

      setState(() {
        _progress = 0.85;
        _status = 'Loading model into memory...';
      });

      await FlutterGemma.getActiveModel(
        maxTokens: 512,
        preferredBackend: PreferredBackend.gpu,
      );

      setState(() {
        _progress = 1.0;
        _isReady = true;
        _status = 'Ready!';
      });

      await Future.delayed(const Duration(milliseconds: 500));
      if (!mounted) return;

      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
            builder: (_) =>
                const DashboardScreen(modelLoaded: true)),
      );
    } catch (e) {
      _progressTimer?.cancel();
      if (!mounted) return;
      setState(() {
        _hasError = true;
        _errorMessage = e.toString();
        _status = 'Error';
      });
    }
  }

  void _startProgressPolling(String modelPath) {
    _progressTimer =
        Timer.periodic(const Duration(seconds: 1), (_) async {
      try {
        final file = File(modelPath);
        if (await file.exists()) {
          final size = await file.length();
          if (size > 0 && mounted) {
            final pct =
                (size / _expectedModelSize * 100).clamp(0.0, 100.0);
            final sizeMB = (size / 1000000).toInt();
            setState(() {
              _progress = 0.05 + (pct / 100.0) * 0.75;
              _status =
                  'Downloading... ${pct.toInt()}% ($sizeMB MB)';
            });
          }
        }
      } catch (_) {}
    });
  }

  @override
  Widget build(BuildContext context) {
    final pctText = '${(_progress * 100).toInt()}%';

    return Scaffold(
      backgroundColor: MalaikaColors.surface,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 48),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Logo
              Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  color: MalaikaColors.primaryLight,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: const Icon(Icons.favorite_rounded,
                    size: 36, color: MalaikaColors.primary),
              ),
              const SizedBox(height: 20),
              const Text('Malaika',
                  style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w700,
                      color: MalaikaColors.text,
                      letterSpacing: -0.5)),
              const SizedBox(height: 4),
              const Text('WHO IMCI Child Health AI',
                  style: TextStyle(
                      fontSize: 14,
                      color: MalaikaColors.textSecondary)),
              const SizedBox(height: 4),
              Text('Powered by Gemma 4 \u2014 Fully Offline',
                  style: TextStyle(
                      fontSize: 12,
                      color: MalaikaColors.textMuted)),
              const SizedBox(height: 48),
              // Progress bar
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: _progress,
                  minHeight: 6,
                  backgroundColor: MalaikaColors.surfaceAlt,
                  valueColor: AlwaysStoppedAnimation(
                    _hasError
                        ? MalaikaColors.red
                        : _isReady
                            ? MalaikaColors.green
                            : MalaikaColors.primary,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              // Status text
              Text(_status,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                      fontSize: 13,
                      color: _hasError
                          ? MalaikaColors.red
                          : _isReady
                              ? MalaikaColors.green
                              : MalaikaColors.textSecondary)),
              // Percentage
              if (!_hasError && !_isReady)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(pctText,
                      style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.w600,
                          color: MalaikaColors.primary)),
                ),
              // Error
              if (_hasError) ...[
                const SizedBox(height: 8),
                Text(_errorMessage,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                        fontSize: 10,
                        color: MalaikaColors.red
                            .withValues(alpha: 0.7))),
                const SizedBox(height: 16),
                TextButton(
                  onPressed: () =>
                      Navigator.of(context).pushReplacement(
                    MaterialPageRoute(
                        builder: (_) => const DashboardScreen(
                            modelLoaded: false)),
                  ),
                  child: const Text('Continue without model'),
                ),
              ],
              const SizedBox(height: 48),
              // Offline badge
              Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  border: Border.all(
                      color: MalaikaColors.green
                          .withValues(alpha: 0.3)),
                  borderRadius: BorderRadius.circular(20),
                  color: MalaikaColors.greenLight,
                ),
                child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.wifi_off_rounded,
                          size: 14, color: MalaikaColors.green),
                      SizedBox(width: 6),
                      Text('Works offline after download',
                          style: TextStyle(
                              fontSize: 12,
                              color: MalaikaColors.green,
                              fontWeight: FontWeight.w500)),
                    ]),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
