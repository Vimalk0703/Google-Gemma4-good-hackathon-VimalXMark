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
  int _speakSeq = 0;
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

      // Make _tts.speak() resolve at audio completion (not at queue time).
      // Without this, the speak future fires immediately after queueing and
      // we cannot distinguish "completed naturally" from "queued but silent".
      await _tts.awaitSpeakCompletion(true);

      // Completion / error fire onSpeakingDone via _finishSpeaking. The
      // cancel handler is intentionally NOT wired to _finishSpeaking:
      // cancellations originate from either (a) speak() stopping a prior
      // utterance to start a new one — the new utterance will fire its own
      // completion later, so firing here would be premature; or
      // (b) stopSpeaking() — that path already calls _finishSpeaking itself.
      // Wiring the cancel handler caused a spurious onSpeakingDone that the
      // home screen interpreted as "TTS done, start STT" while the new
      // utterance was just beginning — voice would cut out audibly.
      _tts.setCompletionHandler(_finishSpeaking);
      _tts.setErrorHandler((msg) {
        debugPrint('[VOICE] TTS error: $msg');
        _finishSpeaking();
      });
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
        pauseFor: const Duration(seconds: 4),
        // onDevice: true FORCES the offline recognizer. Without this,
        // Android's SpeechRecognizer tries to reach Google's cloud and
        // fires error_server_disconnected when the network is missing —
        // exactly what we hit on the A53 in offline-only operation.
        listenOptions: SpeechListenOptions(
          listenMode: ListenMode.dictation,
          onDevice: true,
          partialResults: true,
        ),
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

  /// Speak text via TTS.
  ///
  /// Reliability layers (in order of authority):
  ///   1. setCompletionHandler — fires onSpeakingDone when audio truly
  ///      finishes (the source of truth for "speech done").
  ///   2. setErrorHandler — fires onSpeakingDone if the engine reports an
  ///      error during playback.
  ///   3. Watchdog — hard backstop if the engine wedges mid-speech and
  ///      neither handler fires.
  ///
  /// Concurrency: each call increments _speakSeq. When this call's stop()
  /// later resolves, any handlers from the PREVIOUS utterance that fire
  /// async are matched against _speakSeq and short-circuited — without
  /// this, an earlier utterance's deferred .then() would call
  /// _finishSpeaking on the new utterance and cut its audio short.
  Future<void> speak(String text) async {
    if (!_ttsEnabled || text.isEmpty) {
      onSpeakingDone?.call();
      return;
    }

    // Bump the sequence and clear _isSpeaking BEFORE stopping the engine.
    // Any handler from the previous utterance that fires during stop() will
    // see _isSpeaking == false and short-circuit in _finishSpeaking, so the
    // home screen does not receive a spurious "speech done" mid-replacement.
    final mySeq = ++_speakSeq;
    _isSpeaking = false;
    _ttsWatchdog?.cancel();
    _ttsWatchdog = null;

    // Stop any in-flight TTS and STT — overlapping audio sessions are the
    // single biggest cause of "speaking but no audio".
    try { await _tts.stop(); } catch (_) {}
    if (_stt.isListening) {
      try { await _stt.stop(); } catch (_) {}
    }

    // Always wait for the audio session to switch back to MEDIA before the
    // new speak. Even when STT was not running, the TTS engine itself needs
    // a beat after stop() to fully release its audio track — without this
    // delay, ~1 in 3 utterances on the Samsung A53 plays silently: speak()
    // returns success and the completion handler fires, but no audio ever
    // reaches the speaker. 250ms is the minimum that reliably works on A53.
    await Future.delayed(const Duration(milliseconds: 250));

    // Bail if a newer speak() came in while we were stopping/waiting.
    if (mySeq != _speakSeq) return;

    _isSpeaking = true;
    final wordCount = text.split(RegExp(r'\s+')).length;
    final estimateMs = (wordCount * 500 + 4000).clamp(4000, 30000);
    _ttsWatchdog = Timer(Duration(milliseconds: estimateMs), () {
      if (mySeq == _speakSeq && _isSpeaking) {
        debugPrint('[VOICE] TTS watchdog fired after ${estimateMs}ms — forcing onSpeakingDone');
        _finishSpeaking();
      }
    });

    // Fire-and-forget. With awaitSpeakCompletion(true) the future resolves
    // at completion (or cancellation) — we use it only to detect "engine
    // refused" (result != 1) so the watchdog doesn't have to wait it out.
    // The seq guard prevents the previous utterance's late-resolving future
    // from firing _finishSpeaking after a new speak() has started.
    _tts.speak(text).then((result) {
      if (mySeq != _speakSeq) return;
      if (result != 1) {
        debugPrint('[VOICE] TTS speak returned $result — engine skipped audio');
        _finishSpeaking();
      }
    }).catchError((e) {
      if (mySeq != _speakSeq) return;
      debugPrint('[VOICE] TTS speak error: $e');
      _finishSpeaking();
    });
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
