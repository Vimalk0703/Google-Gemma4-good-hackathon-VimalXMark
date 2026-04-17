/// Gemma 4 E2B inference via flutter_gemma (Google's on-device SDK).
///
/// Uses LiteRT-LM format (.litertlm) for optimal on-device performance.
/// Supports text on both iOS and Android.
/// Supports vision (image input) on Android.
library;

import 'dart:typed_data';
import 'package:flutter_gemma/flutter_gemma.dart';
import 'inference_service.dart';

/// On-device Gemma 4 E2B inference using flutter_gemma.
class GemmaInferenceService implements InferenceService {
  bool _isLoaded = false;

  @override
  bool get isModelLoaded => _isLoaded;

  @override
  bool get supportsVision {
    // flutter_gemma supports vision on Android but not iOS currently
    // This can be updated as the SDK evolves
    return false; // Conservative — enable per-platform when tested
  }

  @override
  Future<void> loadModel(String modelPath) async {
    await FlutterGemmaPlugin.instance.init(
      maxTokens: 1024,
      temperature: 0.4,
      topK: 40,
      topP: 0.95,
    );
    _isLoaded = true;
  }

  @override
  Future<String> generate(
    String prompt, {
    String? systemInstruction,
    int maxTokens = 512,
  }) async {
    if (!_isLoaded) throw StateError('Model not loaded');

    final fullPrompt = systemInstruction != null
        ? '$systemInstruction\n\n$prompt'
        : prompt;

    final response = await FlutterGemmaPlugin.instance.getResponse(
      prompt: fullPrompt,
    );

    return response ?? '';
  }

  @override
  Stream<String> generateStream(
    String prompt, {
    String? systemInstruction,
    int maxTokens = 512,
  }) {
    if (!_isLoaded) throw StateError('Model not loaded');

    final fullPrompt = systemInstruction != null
        ? '$systemInstruction\n\n$prompt'
        : prompt;

    return FlutterGemmaPlugin.instance.getResponseAsync(
      prompt: fullPrompt,
    );
  }

  @override
  Future<String?> analyzeImage(
    Uint8List imageBytes,
    String prompt,
  ) async {
    if (!supportsVision) return null;
    // Vision support via flutter_gemma multimodal API
    // This will be implemented when flutter_gemma adds iOS vision support
    return null;
  }

  @override
  void dispose() {
    _isLoaded = false;
  }
}
