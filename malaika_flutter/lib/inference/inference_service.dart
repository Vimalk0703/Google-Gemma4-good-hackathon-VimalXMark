/// Abstract inference service interface.
///
/// Allows swapping between flutter_gemma (LiteRT) and other backends
/// without changing the chat engine or UI code.
library;

import 'dart:typed_data';

/// Abstract interface for on-device LLM inference.
abstract class InferenceService {
  /// Load the model from a local path.
  Future<void> loadModel(String modelPath);

  /// Whether the model is currently loaded and ready.
  bool get isModelLoaded;

  /// Generate a complete response (non-streaming).
  Future<String> generate(
    String prompt, {
    String? systemInstruction,
    int maxTokens = 512,
  });

  /// Generate a streaming response.
  Stream<String> generateStream(
    String prompt, {
    String? systemInstruction,
    int maxTokens = 512,
  });

  /// Analyze an image with a text prompt (multimodal).
  /// Returns null if vision is not supported on this platform.
  Future<String?> analyzeImage(
    Uint8List imageBytes,
    String prompt,
  );

  /// Whether this engine supports vision (image input) on this platform.
  bool get supportsVision;

  /// Release model resources.
  void dispose();
}
