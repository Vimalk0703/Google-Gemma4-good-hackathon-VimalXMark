/// Gemma 4 E2B inference via llama.cpp (lcpp package).
///
/// Uses GGUF format — lightweight, works offline on iOS and Android.
library;

import 'dart:typed_data';
import 'package:lcpp/lcpp.dart';
import 'inference_service.dart';

/// On-device Gemma 4 E2B inference using llama.cpp.
class GemmaInferenceService implements InferenceService {
  Llama? _llama;

  @override
  bool get isModelLoaded => _llama != null;

  @override
  bool get supportsVision => false;

  @override
  Future<void> loadModel(String modelPath) async {
    _llama = Llama(
      modelParams: ModelParams(path: modelPath),
    );
  }

  @override
  Future<String> generate(
    String prompt, {
    String? systemInstruction,
    int maxTokens = 512,
  }) async {
    if (_llama == null) throw StateError('Model not loaded');

    final messages = <ChatMessage>[];
    if (systemInstruction != null) {
      messages.add(SystemChatMessage(systemInstruction));
    }
    messages.add(UserChatMessage(prompt));

    final buffer = StringBuffer();
    await for (final token in _llama!.prompt(messages)) {
      buffer.write(token);
      if (buffer.length > maxTokens * 4) break;
    }
    return buffer.toString().trim();
  }

  @override
  Stream<String> generateStream(
    String prompt, {
    String? systemInstruction,
    int maxTokens = 512,
  }) {
    if (_llama == null) throw StateError('Model not loaded');

    final messages = <ChatMessage>[];
    if (systemInstruction != null) {
      messages.add(SystemChatMessage(systemInstruction));
    }
    messages.add(UserChatMessage(prompt));

    return _llama!.prompt(messages);
  }

  @override
  Future<String?> analyzeImage(Uint8List imageBytes, String prompt) async {
    return null;
  }

  @override
  void dispose() {
    _llama?.stop();
    _llama = null;
  }
}
