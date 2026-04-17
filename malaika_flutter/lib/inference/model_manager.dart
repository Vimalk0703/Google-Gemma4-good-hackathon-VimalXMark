/// Model download and cache manager.
///
/// Handles downloading the 2.58GB Gemma 4 E2B model from HuggingFace,
/// caching it locally, and validating the download.
library;

import 'package:flutter_gemma/flutter_gemma.dart';

/// Manages Gemma 4 E2B model download and caching.
class ModelManager {
  /// Whether the model is already downloaded and cached.
  Future<bool> isModelCached() async {
    return FlutterGemmaPlugin.instance.isModelLoaded;
  }

  /// Download the model with progress callback.
  ///
  /// The [onProgress] callback receives a value between 0.0 and 1.0.
  /// Returns when download is complete.
  Stream<double> downloadModel() {
    return FlutterGemmaPlugin.instance
        .installModel()
        .fromNetwork()
        .withProgress()
        .execute();
  }

  /// Load the model into memory for inference.
  Future<void> loadModel() async {
    await FlutterGemmaPlugin.instance.init(
      maxTokens: 1024,
      temperature: 0.4,
      topK: 40,
      topP: 0.95,
    );
  }
}
