import 'package:flutter/material.dart';
import 'package:flutter_gemma/flutter_gemma.dart';
import '../theme/malaika_theme.dart';
import 'home_screen.dart';

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

  @override
  void initState() {
    super.initState();
    _initializeApp();
  }

  Future<void> _initializeApp() async {
    try {
      setState(() => _status = 'Initializing Gemma framework...');
      await FlutterGemma.initialize(
        huggingFaceToken: const String.fromEnvironment('HF_TOKEN'),
      );
      setState(() => _progress = 0.1);

      // Install Gemma 4 E2B model from HuggingFace
      setState(() => _status = 'Downloading Gemma 4 E2B...');

      await FlutterGemma.installModel(
        modelType: ModelType.gemmaIt,
        fileType: ModelFileType.litertlm,
      ).fromNetwork(
        'https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm/resolve/main/gemma-4-E2B-it.litertlm',
        token: const String.fromEnvironment('HF_TOKEN'),
      ).withProgress((progress) {
        if (mounted) {
          setState(() {
            _progress = 0.1 + progress * 0.7;
            _status = 'Downloading... ${(progress * 100).toInt()}%';
          });
        }
      }).install();

      setState(() {
        _progress = 0.9;
        _status = 'Loading model...';
      });

      // Get active model with GPU backend for fast inference
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
        MaterialPageRoute(builder: (_) => const HomeScreen(modelLoaded: true)),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _hasError = true;
        _errorMessage = e.toString();
        _status = 'Error';
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
              const Text('Malaika',
                style: TextStyle(fontSize: 36, fontWeight: FontWeight.w600,
                  color: MalaikaColors.primary, letterSpacing: 1)),
              const SizedBox(height: 4),
              const Text('WHO IMCI Child Health AI',
                style: TextStyle(fontSize: 13, color: MalaikaColors.textMuted)),
              const SizedBox(height: 8),
              Text('Powered by Gemma 4 — Fully Offline',
                style: TextStyle(fontSize: 11,
                  color: MalaikaColors.textMuted.withValues(alpha: 0.6))),
              const SizedBox(height: 48),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: _progress, minHeight: 6,
                  backgroundColor: Colors.white.withValues(alpha: 0.06),
                  valueColor: AlwaysStoppedAnimation(
                    _hasError ? MalaikaColors.red
                    : _isReady ? MalaikaColors.green
                    : MalaikaColors.primary),
                ),
              ),
              const SizedBox(height: 16),
              Text(_status, textAlign: TextAlign.center,
                style: TextStyle(fontSize: 13,
                  color: _hasError ? MalaikaColors.red
                  : _isReady ? MalaikaColors.green
                  : MalaikaColors.textMuted)),
              if (_hasError) ...[
                const SizedBox(height: 8),
                Text(_errorMessage, textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 9,
                    color: MalaikaColors.red.withValues(alpha: 0.7))),
                const SizedBox(height: 16),
                TextButton(
                  onPressed: () => Navigator.of(context).pushReplacement(
                    MaterialPageRoute(builder: (_) => const HomeScreen(modelLoaded: false))),
                  child: const Text('Continue without model'),
                ),
              ],
              if (!_hasError && !_isReady)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text('${(_progress * 100).toInt()}%',
                    style: TextStyle(fontSize: 11,
                      color: MalaikaColors.textMuted.withValues(alpha: 0.5))),
                ),
              const SizedBox(height: 48),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  border: Border.all(color: MalaikaColors.green.withValues(alpha: 0.3)),
                  borderRadius: BorderRadius.circular(20),
                  color: MalaikaColors.green.withValues(alpha: 0.06)),
                child: const Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.wifi_off, size: 14, color: MalaikaColors.green),
                  SizedBox(width: 6),
                  Text('Works offline after download',
                    style: TextStyle(fontSize: 11, color: MalaikaColors.green)),
                ]),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
