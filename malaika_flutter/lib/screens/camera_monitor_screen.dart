/// Photo Assessment Screen — single-photo visual assessment via Gemma 4 E2B.
///
/// Launches the headless `CaptureScreen` (native Camera2 + ImageReader, no
/// SurfaceView) to acquire a photo, then runs Gemma 4 vision analysis for
/// alertness, dehydration signs, visible wasting, and edema.
///
/// WHY headless capture (not standard camera or gallery):
/// - Gemma 4 E2B occupies ~2.3GB of ~2.5GB Mali GPU memory
/// - A normal camera preview SurfaceView allocates an EGL/GPU texture and
///   crashes the Mali driver (GPU OOM) on the A53
/// - System camera intent OOM-kills the backgrounded app
/// - Headless Camera2 with `ImageReader` keeps frames in CPU-readable
///   gralloc memory — no GPU surface, no driver pressure
///
/// Chest indrawing is always false — requires observing breathing motion,
/// which a still photo cannot capture.
library;

import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_gemma/flutter_gemma.dart';

import '../core/reconciliation_engine.dart';
import '../theme/malaika_theme.dart';
import 'capture_screen.dart';

/// Result returned to the caller with vision findings.
class CameraMonitorResult {
  final Map<String, VisionFinding> findings;
  final int framesAnalyzed;
  final List<String> notes;

  const CameraMonitorResult({
    required this.findings,
    required this.framesAnalyzed,
    required this.notes,
  });
}

/// Photo-based clinical visual assessment screen.
class CameraMonitorScreen extends StatefulWidget {
  final bool modelLoaded;

  const CameraMonitorScreen({super.key, required this.modelLoaded});

  @override
  State<CameraMonitorScreen> createState() => _CameraMonitorScreenState();
}

class _CameraMonitorScreenState extends State<CameraMonitorScreen> {
  /// Analysis states.
  bool _isAnalyzing = false;
  bool _isComplete = false;
  String? _aiResponse;
  Map<String, bool>? _findings;
  String _notes = '';
  String _statusMessage = 'Tap below to take a photo of the child.';

  /// System instruction — WHO IMCI clinical context.
  static const String _visionSystem =
      'WHO IMCI child health vision assistant. '
      'Report only what you see. If unsure say UNCLEAR.';

  /// Photo prompt — clear separation between what to check and answer format.
  static const String _photoPrompt =
      'Look at this child photo. Check: are eyes open or shut? '
      'Is body limp? Are eyes sunken? Lips dry? Ribs visible? '
      'Limbs thin? Feet swollen?\n'
      'Reply with ONE word per line:\n'
      'ALERTNESS: ALERT or LETHARGIC or UNCONSCIOUS\n'
      'DEHYDRATION: DEHYDRATED or NOT_DEHYDRATED\n'
      'NUTRITION: WASTING or EDEMA or BOTH or NORMAL\n'
      'NOTES: one sentence about what you see';

  // --------------------------------------------------------------------------
  // Image resize
  // --------------------------------------------------------------------------

  Future<Uint8List> _resizeImage(Uint8List jpegBytes) async {
    try {
      final codec = await ui.instantiateImageCodec(
        jpegBytes,
        targetWidth: 160,
      );
      final frame = await codec.getNextFrame();
      final image = frame.image;
      final pngData = await image.toByteData(format: ui.ImageByteFormat.png);
      image.dispose();
      codec.dispose();
      if (pngData != null) {
        return pngData.buffer.asUint8List();
      }
    } catch (e) {
      debugPrint('[MALAIKA] Image resize failed, using original: $e');
    }
    return jpegBytes;
  }

  // --------------------------------------------------------------------------
  // Capture (headless Camera2) + Analyze
  // --------------------------------------------------------------------------

  Future<void> _captureAndAnalyze() async {
    if (_isAnalyzing) return;

    setState(() {
      _isAnalyzing = true;
      _statusMessage = 'Opening camera...';
    });

    try {
      // 1. Headless Camera2 capture — ImageReader only, no GPU surface.
      final rawBytes = await Navigator.of(context).push<Uint8List>(
        MaterialPageRoute(
          builder: (_) => const CaptureScreen(
            title: 'Photo Assessment',
            hint: 'Frame the whole child. Good light. Hold steady.',
          ),
        ),
      );

      if (rawBytes == null || rawBytes.isEmpty) {
        if (mounted) {
          setState(() {
            _isAnalyzing = false;
            _statusMessage = 'No photo taken. Tap to try again or skip.';
          });
        }
        return;
      }

      debugPrint('[MALAIKA] Photo captured: ${rawBytes.length} bytes '
          '(${(rawBytes.length / 1024).toStringAsFixed(0)} KB)');

      setState(() => _statusMessage = 'Preparing image...');

      // 2. Resize for model input.
      final imageBytes = await _resizeImage(rawBytes);
      debugPrint('[MALAIKA] Resized to: ${imageBytes.length} bytes '
          '(${(imageBytes.length / 1024).toStringAsFixed(0)} KB)');

      setState(() => _statusMessage = 'Gemma 4 analyzing photo...');

      // 3. Run vision analysis — no camera active, full GPU for model.
      final analysis = await _analyzePhoto(imageBytes);

      if (analysis != null && analysis.length > 10 && mounted) {
        final parsed = _parseResponse(analysis);
        final notes = _extractNotes(analysis);

        debugPrint('[MALAIKA] ===== VISION OUTPUT =====');
        debugPrint('[MALAIKA] Raw response: $analysis');
        debugPrint('[MALAIKA] Parsed findings: $parsed');
        debugPrint('[MALAIKA] Notes: $notes');
        debugPrint('[MALAIKA] ===========================');

        setState(() {
          _aiResponse = analysis;
          _findings = parsed;
          _notes = notes;
          _isComplete = true;
          _statusMessage = 'Analysis complete. Returning results...';
        });

        // Auto-return results after brief display.
        await Future.delayed(const Duration(seconds: 3));
        if (mounted && _isComplete) {
          _completeAssessment();
          return;
        }
      } else {
        debugPrint('[MALAIKA] Vision analysis returned null/short. '
            'Response: "${analysis ?? "null"}"');
        setState(() {
          _statusMessage = 'Could not analyze photo. Tap X to continue.';
          _isAnalyzing = false;
        });
      }
    } catch (e) {
      debugPrint('[MALAIKA] Photo analysis error: $e');
      setState(() {
        _statusMessage = 'Vision error. Tap X to continue without photo.';
        _isAnalyzing = false;
      });
    }
  }

  Future<String?> _analyzePhoto(Uint8List imageBytes) async {
    dynamic visionChat;
    try {
      final model = await FlutterGemma.getActiveModel(
        maxTokens: 512,
        supportImage: true,
        maxNumImages: 1,
      );
      visionChat = await model.createChat(
        temperature: 0.1,
        topK: 20,
        supportImage: true,
        systemInstruction: _visionSystem,
      );
      debugPrint('[MALAIKA] Vision session created for photo');
      debugPrint('[MALAIKA] ===== VISION INPUT =====');
      debugPrint('[MALAIKA] Image: ${imageBytes.length} bytes '
          '(${(imageBytes.length / 1024).toStringAsFixed(1)} KB)');
      debugPrint('[MALAIKA] Prompt: $_photoPrompt');
      debugPrint('[MALAIKA] ==========================');

      await visionChat.addQuery(Message(
        text: _photoPrompt,
        isUser: true,
        imageBytes: imageBytes,
      ));

      final response = await visionChat.generateChatResponse();

      if (response is TextResponse) {
        return response.token.trim();
      }
      return null;
    } catch (e) {
      debugPrint('[MALAIKA] Gemma vision error: $e');
      return null;
    } finally {
      try { await (visionChat as dynamic)?.close(); } catch (_) {}
    }
  }

  // --------------------------------------------------------------------------
  // Parsing
  // --------------------------------------------------------------------------

  Map<String, bool> _parseResponse(String response) {
    final upper = response.toUpperCase();

    String valueFor(String label) {
      final pattern = RegExp('$label\\s*:\\s*(.+)', caseSensitive: false);
      final match = pattern.firstMatch(upper);
      return match?.group(1)?.trim() ?? '';
    }

    final alertVal = valueFor('ALERTNESS');
    final dehydVal = valueFor('DEHYDRATION');
    final nutriVal = valueFor('NUTRITION');

    return {
      'lethargic': alertVal.startsWith('LETHARGIC') ||
          alertVal.startsWith('UNCONSCIOUS'),
      'chest_indrawing': false,
      'dehydration': dehydVal.startsWith('DEHYDRATED') &&
          !dehydVal.startsWith('NOT'),
      'wasting': nutriVal.startsWith('WASTING') ||
          nutriVal.startsWith('BOTH'),
      'edema': nutriVal.startsWith('EDEMA') ||
          nutriVal.startsWith('BOTH'),
    };
  }

  String _extractNotes(String response) {
    for (final line in response.split('\n')) {
      if (line.toUpperCase().startsWith('NOTES:')) {
        return line.substring(6).trim();
      }
    }
    return '';
  }

  // --------------------------------------------------------------------------
  // Actions
  // --------------------------------------------------------------------------

  void _completeAssessment() {
    if (_findings == null) return;

    final visionFindings = <String, VisionFinding>{};
    for (final entry in _findings!.entries) {
      visionFindings[entry.key] = VisionFinding(
        key: entry.key,
        detectedCount: entry.value ? 1 : 0,
        totalFrames: 1,
      );
    }

    Navigator.of(context).pop(CameraMonitorResult(
      findings: visionFindings,
      framesAnalyzed: 1,
      notes: _notes.isNotEmpty ? [_notes] : [],
    ));
  }

  void _skip() {
    if (_isComplete && _findings != null) {
      _completeAssessment();
      return;
    }
    Navigator.of(context).pop(null);
  }

  // --------------------------------------------------------------------------
  // Build
  // --------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (didPop) return;
        _skip();
      },
      child: Scaffold(
        backgroundColor: Colors.black,
        body: SafeArea(
          child: Column(
            children: [
              _buildHeader(),
              Expanded(child: _isComplete ? _buildResults() : _buildPrompt()),
              _buildControls(),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: Colors.black,
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.close, color: Colors.white),
            onPressed: _skip,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Photo Assessment',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  _statusMessage,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.7),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          if (_isAnalyzing && !_isComplete)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: MalaikaColors.primary.withValues(alpha: 0.8),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  ),
                  SizedBox(width: 6),
                  Text(
                    'ANALYZING',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1,
                    ),
                  ),
                ],
              ),
            ),
          if (_isComplete)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                color: MalaikaColors.green.withValues(alpha: 0.8),
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.check_circle, color: Colors.white, size: 14),
                  SizedBox(width: 4),
                  Text(
                    'DONE',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildPrompt() {
    if (_isAnalyzing) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(color: Colors.white),
            const SizedBox(height: 16),
            const Text(
              'Gemma 4 is analyzing the photo...',
              style: TextStyle(color: Colors.white70, fontSize: 14),
            ),
            const SizedBox(height: 8),
            Text(
              'This takes about 25 seconds',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.4),
                fontSize: 12,
              ),
            ),
          ],
        ),
      );
    }

    // Show captured image if available, otherwise show instructions
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                color: MalaikaColors.primary.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(24),
              ),
              child: const Icon(
                Icons.camera_alt_rounded,
                size: 40,
                color: MalaikaColors.primary,
              ),
            ),
            const SizedBox(height: 24),
            const Text(
              'Visual Assessment',
              style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Take a photo of the child showing their face and body. '
              'Gemma 4 will check for signs of dehydration, wasting, '
              'and alertness — fully on-device.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.6),
                fontSize: 13,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 24),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.1),
                ),
              ),
              child: Column(
                children: [
                  _tipRow(Icons.visibility, 'Face clearly visible'),
                  const SizedBox(height: 8),
                  _tipRow(Icons.child_care, 'Body visible (arms, chest)'),
                  const SizedBox(height: 8),
                  _tipRow(Icons.light_mode, 'Good lighting'),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _tipRow(IconData icon, String text) {
    return Row(
      children: [
        Icon(icon, size: 16, color: MalaikaColors.primary),
        const SizedBox(width: 10),
        Text(
          text,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.6),
            fontSize: 12,
          ),
        ),
      ],
    );
  }

  Widget _buildResults() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Findings card
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1E1E1E),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.check_circle_rounded,
                        color: MalaikaColors.green, size: 16),
                    SizedBox(width: 8),
                    Text(
                      'Photo Analysis Complete',
                      style: TextStyle(
                        color: MalaikaColors.green,
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                if (_findings != null) ...[
                  _findingRow('Alertness', 'lethargic',
                      trueLabel: 'LETHARGIC', falseLabel: 'ALERT'),
                  _findingRow('Dehydration', 'dehydration',
                      trueLabel: 'DETECTED', falseLabel: 'NONE'),
                  _findingRow('Wasting', 'wasting',
                      trueLabel: 'DETECTED', falseLabel: 'NONE'),
                  _findingRow('Edema', 'edema',
                      trueLabel: 'DETECTED', falseLabel: 'NONE'),
                  const SizedBox(height: 8),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.05),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.info_outline,
                            size: 14, color: Colors.white38),
                        const SizedBox(width: 6),
                        Expanded(
                          child: Text(
                            'Chest indrawing requires breathing observation '
                            '(assessed during Q&A)',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.4),
                              fontSize: 11,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 12),
          // Raw AI response
          if (_aiResponse != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFF1E1E1E),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.white12),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.psychology_rounded,
                          size: 14, color: Colors.white38),
                      SizedBox(width: 6),
                      Text(
                        'What Gemma 4 Sees',
                        style: TextStyle(
                          color: Colors.white54,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    _aiResponse!,
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 12,
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _findingRow(
    String label,
    String key, {
    required String trueLabel,
    required String falseLabel,
  }) {
    final detected = _findings?[key] ?? false;
    final color = detected ? MalaikaColors.yellow : MalaikaColors.green;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text(label,
                style: const TextStyle(color: Colors.white70, fontSize: 13)),
          ),
          Icon(
            detected
                ? Icons.warning_amber_rounded
                : Icons.check_circle_rounded,
            color: color,
            size: 16,
          ),
          const SizedBox(width: 8),
          Text(
            detected ? trueLabel : falseLabel,
            style: TextStyle(
              color: color,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildControls() {
    return Container(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 12,
        bottom: MediaQuery.of(context).padding.bottom + 12,
      ),
      color: Colors.black,
      child: Row(
        children: [
          if (!_isComplete)
            Expanded(
              child: OutlinedButton(
                onPressed: _isAnalyzing ? null : _skip,
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white70,
                  side: const BorderSide(color: Colors.white24),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Text('Skip'),
              ),
            ),
          if (!_isComplete) const SizedBox(width: 12),
          Expanded(
            child: ElevatedButton.icon(
              onPressed: _isAnalyzing
                  ? null
                  : _isComplete
                      ? _completeAssessment
                      : _captureAndAnalyze,
              icon: Icon(
                _isComplete
                    ? Icons.check_rounded
                    : Icons.camera_alt_rounded,
                size: 20,
              ),
              label: Text(
                _isComplete ? 'Use Results' : 'Take Photo',
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor:
                    _isComplete ? MalaikaColors.green : MalaikaColors.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                elevation: 0,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
