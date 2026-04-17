/// Model download and cache manager for GGUF models.
///
/// Downloads Gemma 4 E2B GGUF from HuggingFace, caches locally.
/// After first download, zero internet needed.
library;

import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

/// Manages Gemma 4 E2B GGUF model download and caching.
class ModelManager {
  /// HuggingFace URL for Gemma 4 E2B Q4_K_M GGUF.
  /// This is the smallest useful quantization (~1.8GB).
  static const modelUrl =
      'https://huggingface.co/unsloth/gemma-4-E2B-it-GGUF/resolve/main/gemma-4-E2B-it-Q4_K_M.gguf';

  static const modelFilename = 'gemma-4-e2b-q4.gguf';

  /// Get the directory where models are stored.
  static Future<String> get _modelDir async {
    final dir = await getApplicationDocumentsDirectory();
    final modelDir = Directory('${dir.path}/models');
    if (!await modelDir.exists()) {
      await modelDir.create(recursive: true);
    }
    return modelDir.path;
  }

  /// Full path to the model file.
  static Future<String> get modelPath async {
    final dir = await _modelDir;
    return '$dir/$modelFilename';
  }

  /// Check if model is already downloaded.
  static Future<bool> isModelCached() async {
    final path = await modelPath;
    final file = File(path);
    if (!await file.exists()) return false;
    // Basic size check — Q4_K_M should be > 1GB
    final size = await file.length();
    return size > 1000000000;
  }

  /// Download model with progress callback.
  /// Returns the local file path when complete.
  static Future<String> downloadModel({
    void Function(double progress)? onProgress,
  }) async {
    final path = await modelPath;
    final file = File(path);

    // Already downloaded?
    if (await isModelCached()) {
      onProgress?.call(1.0);
      return path;
    }

    // Download with progress
    final request = http.Request('GET', Uri.parse(modelUrl));
    final response = await http.Client().send(request);

    if (response.statusCode != 200) {
      throw Exception('Model download failed: HTTP ${response.statusCode}');
    }

    final totalBytes = response.contentLength ?? 0;
    var receivedBytes = 0;

    final sink = file.openWrite();

    await for (final chunk in response.stream) {
      sink.add(chunk);
      receivedBytes += chunk.length;
      if (totalBytes > 0) {
        onProgress?.call(receivedBytes / totalBytes);
      }
    }

    await sink.flush();
    await sink.close();

    // Verify download
    final downloadedSize = await file.length();
    if (downloadedSize < 1000000000) {
      await file.delete();
      throw Exception('Model download incomplete: ${downloadedSize ~/ 1000000}MB');
    }

    return path;
  }

  /// Delete cached model to free space.
  static Future<void> deleteModel() async {
    final path = await modelPath;
    final file = File(path);
    if (await file.exists()) {
      await file.delete();
    }
  }
}
