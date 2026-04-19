/// Camera Monitor Screen — real-time visual assessment via Gemma 4 E2B.
///
/// After the questionnaire completes, this screen opens the camera and
/// periodically captures frames for Gemma 4 vision analysis. It checks
/// for: alertness, chest indrawing, dehydration signs, and wasting/edema.
///
/// The findings accumulate across frames to build confidence. When enough
/// frames are analyzed (or the user presses "Complete"), the aggregated
/// vision findings are returned to the caller for reconciliation.
library;

import 'dart:async';
import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter_gemma/flutter_gemma.dart';

import '../core/reconciliation_engine.dart';
import '../theme/malaika_theme.dart';

/// Result returned to the caller with aggregated vision findings.
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

/// Full-screen camera monitor for clinical visual assessment.
class CameraMonitorScreen extends StatefulWidget {
  /// Whether the Gemma 4 model is loaded and ready.
  final bool modelLoaded;

  const CameraMonitorScreen({super.key, required this.modelLoaded});

  @override
  State<CameraMonitorScreen> createState() => _CameraMonitorScreenState();
}

class _CameraMonitorScreenState extends State<CameraMonitorScreen>
    with WidgetsBindingObserver {
  CameraController? _cameraController;
  bool _isCameraReady = false;
  bool _isAnalyzing = false;
  bool _isCapturing = false;
  bool _isComplete = false;

  /// Aggregates findings across frames.
  final VisionAggregator _aggregator = VisionAggregator();

  /// Timer for periodic frame capture.
  Timer? _captureTimer;

  /// Current status message.
  String _statusMessage = 'Initializing camera...';

  /// Target number of frames to analyze.
  static const int _targetFrames = 6;

  /// Interval between frame captures (seconds).
  static const int _captureIntervalSec = 4;

  /// The clinical vision prompt — checks ALL signs in one pass.
  static const String _clinicalPrompt =
      'You are a clinical health assistant performing a visual assessment '
      'of a child. Analyze this image and report on ALL of the following.\n\n'
      'CHECK EACH ITEM:\n'
      '1. ALERTNESS: Is the child alert and responsive, lethargic (abnormally '
      'sleepy, not looking at camera), or unconscious?\n'
      '2. CHEST: If the chest is visible, is there chest indrawing (lower '
      'chest wall pulls inward when breathing)?\n'
      '3. DEHYDRATION: Are the eyes sunken? Does the skin look dry? Are '
      'lips cracked?\n'
      '4. NUTRITION: Is the child very thin (ribs/bones visible = wasting)? '
      'Is there swelling in both feet (edema)?\n\n'
      'RESPOND IN EXACTLY THIS FORMAT (one line per item):\n'
      'ALERTNESS: ALERT or LETHARGIC or UNCONSCIOUS\n'
      'CHEST: INDRAWING or NO_INDRAWING or NOT_VISIBLE\n'
      'DEHYDRATION: DEHYDRATED or NOT_DEHYDRATED\n'
      'NUTRITION: WASTING or EDEMA or BOTH or NORMAL\n'
      'NOTES: One sentence observation about the child';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initCamera();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _captureTimer?.cancel();
    _cameraController?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return;
    }
    if (state == AppLifecycleState.inactive) {
      _captureTimer?.cancel();
      _cameraController?.dispose();
      _cameraController = null;
    } else if (state == AppLifecycleState.resumed) {
      _initCamera();
    }
  }

  // --------------------------------------------------------------------------
  // Camera Initialization
  // --------------------------------------------------------------------------

  Future<void> _initCamera() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        setState(() => _statusMessage = 'No camera available');
        return;
      }

      // Prefer back camera for clinical assessment.
      final camera = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );

      _cameraController = CameraController(
        camera,
        ResolutionPreset.medium,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );

      await _cameraController!.initialize();
      if (!mounted) return;

      setState(() {
        _isCameraReady = true;
        _statusMessage = 'Camera ready. Tap "Start Scan" to begin.';
      });
    } catch (e) {
      debugPrint('[MALAIKA] Camera init error: $e');
      setState(() => _statusMessage = 'Camera error: $e');
    }
  }

  // --------------------------------------------------------------------------
  // Frame Capture & Analysis
  // --------------------------------------------------------------------------

  void _startMonitoring() {
    if (!_isCameraReady || !widget.modelLoaded) return;

    setState(() {
      _statusMessage = 'Scanning... Hold camera steady on the child.';
      _isAnalyzing = true;
    });

    // Capture first frame immediately, then every N seconds.
    _captureAndAnalyze();
    _captureTimer = Timer.periodic(
      Duration(seconds: _captureIntervalSec),
      (_) => _captureAndAnalyze(),
    );
  }

  Future<void> _captureAndAnalyze() async {
    if (!mounted || _isCapturing || _isComplete) return;
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return;
    }

    _isCapturing = true;

    try {
      // Capture a photo from the camera.
      final xFile = await _cameraController!.takePicture();
      final imageBytes = await xFile.readAsBytes();

      setState(() {
        _statusMessage =
            'Analyzing frame ${_aggregator.totalFrames + 1}/$_targetFrames...';
      });

      // Send to Gemma 4 for vision analysis.
      final analysis = await _analyzeWithGemma(imageBytes);

      if (analysis != null && mounted) {
        // Parse the structured response.
        final frameFindings = _parseVisionResponse(analysis);
        final notes = _extractNotes(analysis);
        _aggregator.addFrame(frameFindings, notes);

        setState(() {
          _statusMessage = _aggregator.totalFrames >= _targetFrames
              ? 'Scan complete! Review findings below.'
              : 'Frame ${_aggregator.totalFrames}/$_targetFrames analyzed.';
        });
      }

      // Check if we have enough frames.
      if (_aggregator.totalFrames >= _targetFrames) {
        _captureTimer?.cancel();
        setState(() => _isComplete = true);
      }
    } catch (e) {
      debugPrint('[MALAIKA] Capture error: $e');
    } finally {
      _isCapturing = false;
    }
  }

  /// Send image to Gemma 4 E2B for clinical vision analysis.
  Future<String?> _analyzeWithGemma(Uint8List imageBytes) async {
    try {
      final model = await FlutterGemma.getActiveModel(maxTokens: 200);
      final chat = await model.createChat(
        temperature: 0.2,
        topK: 40,
        systemInstruction:
            'You are a clinical health assistant. Analyze images precisely '
            'using the structured format requested. Be accurate and concise.',
      );

      await chat.addQuery(Message(
        text: _clinicalPrompt,
        isUser: true,
        imageBytes: imageBytes,
      ));

      final response = await chat.generateChatResponse();
      await chat.close();

      if (response is TextResponse) {
        final text = response.token.trim();
        debugPrint('[MALAIKA] Vision frame: $text');
        return text;
      }
      return null;
    } catch (e) {
      debugPrint('[MALAIKA] Gemma vision error: $e');
      return null;
    }
  }

  /// Parse structured vision response into boolean findings.
  Map<String, bool> _parseVisionResponse(String response) {
    final upper = response.toUpperCase();
    return {
      'lethargic': upper.contains('LETHARGIC') ||
          upper.contains('UNCONSCIOUS'),
      'chest_indrawing': upper.contains('INDRAWING') &&
          !upper.contains('NO_INDRAWING') &&
          !upper.contains('NO INDRAWING'),
      'dehydration': upper.contains('DEHYDRATED') &&
          !upper.contains('NOT_DEHYDRATED') &&
          !upper.contains('NOT DEHYDRATED'),
      'wasting': upper.contains('WASTING') &&
          !upper.contains('NO WASTING') &&
          !upper.contains('NORMAL'),
      'edema': upper.contains('EDEMA') &&
          !upper.contains('NO EDEMA') &&
          !upper.contains('NO_EDEMA'),
    };
  }

  /// Extract the NOTES line from the response.
  String _extractNotes(String response) {
    for (final line in response.split('\n')) {
      if (line.toUpperCase().startsWith('NOTES:')) {
        return line.substring(6).trim();
      }
    }
    return '';
  }

  void _completeAssessment() {
    final result = CameraMonitorResult(
      findings: _aggregator.findings,
      framesAnalyzed: _aggregator.totalFrames,
      notes: _aggregator.notes,
    );
    Navigator.of(context).pop(result);
  }

  void _skipVision() {
    Navigator.of(context).pop(null);
  }

  // --------------------------------------------------------------------------
  // Build
  // --------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Column(
          children: [
            _buildHeader(),
            Expanded(child: _buildCameraPreview()),
            _buildFindingsOverlay(),
            _buildControls(),
          ],
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
            onPressed: _skipVision,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Vision Assessment',
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
                color: MalaikaColors.red.withValues(alpha: 0.8),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'SCANNING',
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

  Widget _buildCameraPreview() {
    if (!_isCameraReady || _cameraController == null) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: Colors.white),
            SizedBox(height: 16),
            Text(
              'Starting camera...',
              style: TextStyle(color: Colors.white70, fontSize: 14),
            ),
          ],
        ),
      );
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        // Camera preview
        ClipRRect(
          borderRadius: BorderRadius.circular(12),
          child: AspectRatio(
            aspectRatio: _cameraController!.value.aspectRatio,
            child: CameraPreview(_cameraController!),
          ),
        ),
        // Scanning overlay animation
        if (_isAnalyzing && !_isComplete)
          Positioned.fill(
            child: _ScanOverlay(isCapturing: _isCapturing),
          ),
        // Frame counter
        if (_aggregator.totalFrames > 0)
          Positioned(
            top: 12,
            right: 12,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                '${_aggregator.totalFrames}/$_targetFrames',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        // Progress bar
        if (_isAnalyzing)
          Positioned(
            bottom: 0,
            left: 0,
            right: 0,
            child: LinearProgressIndicator(
              value: _aggregator.totalFrames / _targetFrames,
              backgroundColor: Colors.white24,
              valueColor: AlwaysStoppedAnimation<Color>(
                _isComplete ? MalaikaColors.green : MalaikaColors.primary,
              ),
              minHeight: 4,
            ),
          ),
      ],
    );
  }

  Widget _buildFindingsOverlay() {
    final findings = _aggregator.findings;
    if (findings.isEmpty && !_isAnalyzing) {
      return const SizedBox.shrink();
    }

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E1E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                _isComplete
                    ? Icons.check_circle_rounded
                    : Icons.visibility_rounded,
                color: _isComplete ? MalaikaColors.green : Colors.white70,
                size: 16,
              ),
              const SizedBox(width: 8),
              Text(
                _isComplete ? 'Scan Complete' : 'Live Findings',
                style: TextStyle(
                  color: _isComplete ? MalaikaColors.green : Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (_aggregator.totalFrames > 0) ...[
                const Spacer(),
                Text(
                  '${_aggregator.totalFrames} frames',
                  style: const TextStyle(color: Colors.white38, fontSize: 11),
                ),
              ],
            ],
          ),
          if (findings.isNotEmpty) ...[
            const SizedBox(height: 12),
            _findingRow('Alertness', 'lethargic', findings,
                invertLabel: true,
                trueLabel: 'LETHARGIC',
                falseLabel: 'ALERT'),
            _findingRow('Chest', 'chest_indrawing', findings,
                trueLabel: 'INDRAWING',
                falseLabel: 'CLEAR'),
            _findingRow('Dehydration', 'dehydration', findings,
                trueLabel: 'DETECTED',
                falseLabel: 'NONE'),
            _findingRow('Wasting', 'wasting', findings,
                trueLabel: 'DETECTED',
                falseLabel: 'NONE'),
            _findingRow('Edema', 'edema', findings,
                trueLabel: 'DETECTED',
                falseLabel: 'NONE'),
          ] else if (_isAnalyzing) ...[
            const SizedBox(height: 12),
            const Text(
              'Waiting for first frame analysis...',
              style: TextStyle(color: Colors.white38, fontSize: 12),
            ),
          ],
        ],
      ),
    );
  }

  Widget _findingRow(
    String label,
    String key,
    Map<String, VisionFinding> findings, {
    bool invertLabel = false,
    required String trueLabel,
    required String falseLabel,
  }) {
    final finding = findings[key];
    if (finding == null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          children: [
            SizedBox(
              width: 100,
              child: Text(label,
                  style: const TextStyle(color: Colors.white54, fontSize: 12)),
            ),
            const Text('--',
                style: TextStyle(color: Colors.white24, fontSize: 12)),
          ],
        ),
      );
    }

    final detected = finding.detected;
    final isWarning = detected; // Detection = potential concern
    final color = isWarning ? MalaikaColors.yellow : MalaikaColors.green;
    final statusLabel = detected ? trueLabel : falseLabel;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text(label,
                style: const TextStyle(color: Colors.white70, fontSize: 12)),
          ),
          Icon(
            detected
                ? Icons.warning_amber_rounded
                : Icons.check_circle_rounded,
            color: color,
            size: 14,
          ),
          const SizedBox(width: 6),
          Text(
            statusLabel,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          const Spacer(),
          Text(
            finding.confidenceLabel,
            style: const TextStyle(color: Colors.white38, fontSize: 10),
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
          // Skip button
          if (!_isAnalyzing)
            Expanded(
              child: OutlinedButton(
                onPressed: _skipVision,
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.white70,
                  side: const BorderSide(color: Colors.white24),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Text('Skip Vision'),
              ),
            ),
          if (!_isAnalyzing) const SizedBox(width: 12),
          // Start / Complete button
          Expanded(
            flex: _isAnalyzing ? 1 : 1,
            child: ElevatedButton.icon(
              onPressed: _isAnalyzing
                  ? (_aggregator.totalFrames > 0 ? _completeAssessment : null)
                  : _startMonitoring,
              icon: Icon(
                _isComplete
                    ? Icons.check_rounded
                    : _isAnalyzing
                        ? Icons.stop_rounded
                        : Icons.play_arrow_rounded,
                size: 20,
              ),
              label: Text(
                _isComplete
                    ? 'View Results'
                    : _isAnalyzing
                        ? 'Complete (${_aggregator.totalFrames}/$_targetFrames)'
                        : 'Start Scan',
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

// =============================================================================
// Scan Overlay Animation
// =============================================================================

class _ScanOverlay extends StatefulWidget {
  final bool isCapturing;
  const _ScanOverlay({required this.isCapturing});

  @override
  State<_ScanOverlay> createState() => _ScanOverlayState();
}

class _ScanOverlayState extends State<_ScanOverlay>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return CustomPaint(
          painter: _ScanLinePainter(
            progress: _controller.value,
            isCapturing: widget.isCapturing,
          ),
        );
      },
    );
  }
}

class _ScanLinePainter extends CustomPainter {
  final double progress;
  final bool isCapturing;

  _ScanLinePainter({required this.progress, required this.isCapturing});

  @override
  void paint(Canvas canvas, Size size) {
    // Corner brackets
    final bracketPaint = Paint()
      ..color = isCapturing
          ? MalaikaColors.yellow.withValues(alpha: 0.8)
          : MalaikaColors.primary.withValues(alpha: 0.6)
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke;

    const bracketLen = 30.0;
    const margin = 24.0;

    // Top-left
    canvas.drawLine(
        Offset(margin, margin), Offset(margin + bracketLen, margin),
        bracketPaint);
    canvas.drawLine(
        Offset(margin, margin), Offset(margin, margin + bracketLen),
        bracketPaint);
    // Top-right
    canvas.drawLine(Offset(size.width - margin, margin),
        Offset(size.width - margin - bracketLen, margin), bracketPaint);
    canvas.drawLine(Offset(size.width - margin, margin),
        Offset(size.width - margin, margin + bracketLen), bracketPaint);
    // Bottom-left
    canvas.drawLine(Offset(margin, size.height - margin),
        Offset(margin + bracketLen, size.height - margin), bracketPaint);
    canvas.drawLine(Offset(margin, size.height - margin),
        Offset(margin, size.height - margin - bracketLen), bracketPaint);
    // Bottom-right
    canvas.drawLine(
        Offset(size.width - margin, size.height - margin),
        Offset(size.width - margin - bracketLen, size.height - margin),
        bracketPaint);
    canvas.drawLine(
        Offset(size.width - margin, size.height - margin),
        Offset(size.width - margin, size.height - margin - bracketLen),
        bracketPaint);

    // Scanning line
    final lineY =
        margin + (size.height - 2 * margin) * progress;
    final linePaint = Paint()
      ..shader = LinearGradient(
        colors: [
          Colors.transparent,
          MalaikaColors.primary.withValues(alpha: 0.6),
          Colors.transparent,
        ],
      ).createShader(
          Rect.fromLTWH(margin, lineY, size.width - 2 * margin, 2));
    canvas.drawLine(
        Offset(margin, lineY), Offset(size.width - margin, lineY), linePaint);
  }

  @override
  bool shouldRepaint(covariant _ScanLinePainter old) =>
      old.progress != progress || old.isCapturing != isCapturing;
}
