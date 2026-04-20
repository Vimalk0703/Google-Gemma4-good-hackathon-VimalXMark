import 'package:flutter/foundation.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:flutter_tts/flutter_tts.dart';

/// Wraps offline STT (Android SpeechRecognizer) and TTS (Samsung/Google engine).
/// Both run on CPU — no GPU conflict with Gemma 4 E2B.
class VoiceService {
  final SpeechToText _stt = SpeechToText();
  final FlutterTts _tts = FlutterTts();

  bool _sttAvailable = false;
  bool _ttsEnabled = true;

  bool get isSttAvailable => _sttAvailable;
  bool get isTtsEnabled => _ttsEnabled;

  /// Callbacks wired by the screen.
  void Function(String finalText)? onResult;
  void Function(String partialText)? onPartial;
  VoidCallback? onListeningStopped;
  VoidCallback? onSpeakingDone;
  VoidCallback? onError;

  /// Initialize both STT and TTS. Returns true if STT is available.
  Future<bool> init() async {
    // STT — uses Android's built-in SpeechRecognizer (offline with language pack)
    try {
      _sttAvailable = await _stt.initialize(
        onError: (error) {
          debugPrint('[VOICE] STT error: ${error.errorMsg}');
          onError?.call();
        },
        onStatus: (status) {
          debugPrint('[VOICE] STT status: $status');
          if (status == 'notListening' || status == 'done') {
            onListeningStopped?.call();
          }
        },
      );
    } catch (e) {
      debugPrint('[VOICE] STT init failed: $e');
      _sttAvailable = false;
    }

    // TTS — uses Samsung TTS / Google TTS engine (offline, pre-installed)
    try {
      await _tts.setLanguage('en-US');
      await _tts.setSpeechRate(0.45); // Slightly slow for medical context
      await _tts.setVolume(1.0);
      _tts.setCompletionHandler(() => onSpeakingDone?.call());
    } catch (e) {
      debugPrint('[VOICE] TTS init failed: $e');
    }

    debugPrint('[VOICE] Init: stt=$_sttAvailable');
    return _sttAvailable;
  }

  /// Start listening. Auto-stops after 3s silence or 15s max.
  Future<void> startListening() async {
    if (!_sttAvailable) return;
    try {
      await _stt.listen(
        onResult: (result) {
          if (result.finalResult) {
            onResult?.call(result.recognizedWords);
          } else {
            onPartial?.call(result.recognizedWords);
          }
        },
        listenFor: const Duration(seconds: 15),
        pauseFor: const Duration(seconds: 3),
        listenOptions: SpeechListenOptions(listenMode: ListenMode.dictation),
      );
    } catch (e) {
      debugPrint('[VOICE] Listen error: $e');
      onError?.call();
    }
  }

  /// Stop listening early (user taps mic).
  Future<void> stopListening() async {
    try {
      await _stt.stop();
    } catch (_) {}
  }

  /// Speak text via TTS. No-op if TTS is disabled.
  Future<void> speak(String text) async {
    if (!_ttsEnabled || text.isEmpty) {
      onSpeakingDone?.call();
      return;
    }
    try {
      await _tts.speak(text);
    } catch (e) {
      debugPrint('[VOICE] TTS speak error: $e');
      onSpeakingDone?.call();
    }
  }

  /// Interrupt TTS playback.
  Future<void> stopSpeaking() async {
    try {
      await _tts.stop();
    } catch (_) {}
  }

  void toggleTts() => _ttsEnabled = !_ttsEnabled;

  Future<void> dispose() async {
    await _stt.stop();
    await _stt.cancel();
    await _tts.stop();
  }
}
