import 'dart:async';

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
  bool _isSpeaking = false;
  Timer? _ttsWatchdog;

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

    // TTS — prefer Google TTS (neural voices, more natural than Samsung TTS)
    try {
      final engines = await _tts.getEngines;
      debugPrint('[VOICE] TTS engines: $engines');

      // Switch to Google TTS if available
      final engineList = engines is List ? engines : [];
      if (engineList.any((e) => e.toString().contains('google'))) {
        await _tts.setEngine('com.google.android.tts');
        debugPrint('[VOICE] Using Google TTS engine');
      }

      await _tts.setLanguage('en-US');

      // Pick the best available voice
      final voices = await _tts.getVoices;
      if (voices is List) {
        final enVoices = voices
            .where((v) => v is Map &&
                (v['locale']?.toString().startsWith('en') ?? false))
            .toList();
        debugPrint('[VOICE] Found ${enVoices.length} English voices:');
        for (final v in enVoices) {
          debugPrint('[VOICE]   ${v}');
        }
        // Prefer Google's high-quality neural female voices — LOCAL only (offline)
        // tpf = female, iol = female, iob = female, iog = female
        // iom = male, tpc/tpd = male, sfg = male
        final preferredNames = [
          'en-us-x-tpf-local',
          'en-us-x-iol-local',
          'en-us-x-iob-local',
          'en-us-x-iog-local',
        ];
        Map? bestVoice;
        for (final name in preferredNames) {
          final match = enVoices.where((v) =>
              v is Map && v['name']?.toString() == name).firstOrNull;
          if (match != null) {
            bestVoice = match as Map;
            break;
          }
        }
        if (bestVoice != null) {
          await _tts.setVoice({
            'name': bestVoice['name'].toString(),
            'locale': bestVoice['locale'].toString(),
          });
          debugPrint('[VOICE] Selected voice: ${bestVoice['name']}');
        }
      }

      await _tts.setSpeechRate(0.48);
      await _tts.setPitch(1.05); // Slightly warm tone
      await _tts.setVolume(1.0);
      // ALL terminal TTS states — completion, error, cancel — must clear
      // _isSpeaking and fire onSpeakingDone. Without this, audio focus
      // loss or engine errors leave the UI stuck on "speaking".
      _tts.setCompletionHandler(_finishSpeaking);
      _tts.setErrorHandler((msg) {
        debugPrint('[VOICE] TTS error: $msg');
        _finishSpeaking();
      });
      _tts.setCancelHandler(_finishSpeaking);
    } catch (e) {
      debugPrint('[VOICE] TTS init failed: $e');
    }

    debugPrint('[VOICE] Init: stt=$_sttAvailable');
    return _sttAvailable;
  }

  /// Start listening. Auto-stops after 3s silence or 15s max.
  ///
  /// Defensive: if a prior session is still active (Android's SpeechRecognizer
  /// often holds the resource for ~200ms after stop), we explicitly stop and
  /// wait before starting a new session. Without this guard, listen() can
  /// silently no-op and the UI gets stuck showing "listening" while nothing
  /// is actually being recorded.
  Future<void> startListening() async {
    if (!_sttAvailable) return;
    try {
      if (_stt.isListening) {
        await _stt.stop();
        await Future.delayed(const Duration(milliseconds: 250));
      }
      final ok = await _stt.listen(
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
      // The speech_to_text plugin's return value is unreliable on Android —
      // it can return false even when the engine started listening (the
      // status callback "listening" fires regardless). Only log; the
      // status/error callbacks are the authoritative signal.
      if (ok != true) {
        debugPrint('[VOICE] _stt.listen returned false (status callback authoritative)');
      }
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
  ///
  /// A watchdog timer guarantees [onSpeakingDone] fires even if the engine
  /// silently drops the request (audio focus loss, Bluetooth disconnect,
  /// engine swap). Estimate is generous — ~0.5s per word + 3s buffer,
  /// capped at 30s — so genuine completion still wins.
  Future<void> speak(String text) async {
    if (!_ttsEnabled || text.isEmpty) {
      onSpeakingDone?.call();
      return;
    }
    _isSpeaking = true;
    _ttsWatchdog?.cancel();
    final wordCount = text.split(RegExp(r'\s+')).length;
    final estimateMs = (wordCount * 500 + 3000).clamp(3000, 30000);
    _ttsWatchdog = Timer(Duration(milliseconds: estimateMs), () {
      if (_isSpeaking) {
        debugPrint('[VOICE] TTS watchdog fired after ${estimateMs}ms — forcing onSpeakingDone');
        _finishSpeaking();
      }
    });
    try {
      await _tts.speak(text);
    } catch (e) {
      debugPrint('[VOICE] TTS speak error: $e');
      _finishSpeaking();
    }
  }

  void _finishSpeaking() {
    _ttsWatchdog?.cancel();
    _ttsWatchdog = null;
    if (!_isSpeaking) return; // already cleared — don't fire twice
    _isSpeaking = false;
    onSpeakingDone?.call();
  }

  /// Interrupt TTS playback.
  Future<void> stopSpeaking() async {
    try {
      await _tts.stop();
    } catch (_) {}
    _finishSpeaking();
  }

  void toggleTts() => _ttsEnabled = !_ttsEnabled;

  Future<void> dispose() async {
    _ttsWatchdog?.cancel();
    await _stt.stop();
    await _stt.cancel();
    await _tts.stop();
  }
}
