/// CaptureScreen — headless Camera2 photo capture.
///
/// Uses the native MalaikaCameraPlugin (Camera2 + ImageReader) so we never
/// allocate a GPU surface. Live preview is a stuttery still refresh at ~2fps
/// (one Image.memory rebuilt every 500ms from a fresh JPEG buffer). On the
/// A53 this lets us coexist with Gemma 4 E2B on the Mali GPU — full-preview
/// SurfaceView crashes the driver.
///
/// Returns a `Uint8List` of high-resolution JPEG bytes on success, or `null`
/// if the user cancels.
library;

import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../services/malaika_camera.dart';
import '../theme/malaika_theme.dart';

enum _CapturePhase { starting, previewing, capturing, reviewing, error }

class CaptureScreen extends StatefulWidget {
  final String title;
  final String hint;

  const CaptureScreen({
    super.key,
    this.title = 'Take Photo',
    this.hint = 'Frame the whole child. Good light. Hold steady.',
  });

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen>
    with WidgetsBindingObserver {
  static const Duration _previewInterval = Duration(milliseconds: 500);

  _CapturePhase _phase = _CapturePhase.starting;
  Uint8List? _previewBytes;
  Uint8List? _capturedBytes;
  String _statusMessage = 'Starting camera...';
  String? _errorMessage;
  Timer? _previewTimer;
  bool _disposed = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _bootstrap();
  }

  @override
  void dispose() {
    _disposed = true;
    WidgetsBinding.instance.removeObserver(this);
    _previewTimer?.cancel();
    MalaikaCamera.instance.stop();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive) {
      _previewTimer?.cancel();
      MalaikaCamera.instance.stop();
    }
  }

  // --------------------------------------------------------------------------
  // Camera bootstrap
  // --------------------------------------------------------------------------

  Future<void> _bootstrap() async {
    final granted = await MalaikaCamera.instance.requestPermission();
    if (!granted) {
      _showError('Camera permission denied.');
      return;
    }

    // 640×480 is the sweet spot — small enough to dodge LMKD with Gemma
    // loaded, big enough that downstream resize-to-256 still has good
    // signal for clinical IMCI vision (alertness, dehydration, wasting).
    final ok = await MalaikaCamera.instance.start(
      captureWidth: 640,
      captureHeight: 480,
    );
    if (!ok) {
      _showError('Could not start camera.');
      return;
    }
    if (_disposed) return;

    setState(() {
      _phase = _CapturePhase.previewing;
      _statusMessage = 'Hold steady. Tap to capture.';
    });
    _startPreviewLoop();
  }

  void _startPreviewLoop() {
    _previewTimer?.cancel();
    _previewTimer = Timer.periodic(_previewInterval, (_) async {
      if (_disposed || _phase != _CapturePhase.previewing) return;
      final bytes = await MalaikaCamera.instance.pullFrame();
      if (_disposed) return;
      if (bytes != null && bytes.isNotEmpty) {
        setState(() => _previewBytes = bytes);
      }
    });
  }

  void _showError(String message) {
    if (_disposed) return;
    setState(() {
      _phase = _CapturePhase.error;
      _errorMessage = message;
      _statusMessage = message;
    });
  }

  // --------------------------------------------------------------------------
  // Shutter
  // --------------------------------------------------------------------------

  Future<void> _onShutter() async {
    if (_phase != _CapturePhase.previewing) return;
    setState(() {
      _phase = _CapturePhase.capturing;
      _statusMessage = 'Capturing...';
    });
    _previewTimer?.cancel();

    final bytes = await MalaikaCamera.instance.capture();
    if (_disposed) return;

    if (bytes == null || bytes.isEmpty) {
      _showError('Capture failed. Try again.');
      _previewTimer = null;
      _startPreviewLoop();
      return;
    }

    setState(() {
      _capturedBytes = bytes;
      _phase = _CapturePhase.reviewing;
      _statusMessage = 'Review the photo.';
    });
  }

  void _onRetake() {
    setState(() {
      _capturedBytes = null;
      _phase = _CapturePhase.previewing;
      _statusMessage = 'Hold steady. Tap to capture.';
    });
    _startPreviewLoop();
  }

  void _onUse() {
    if (_capturedBytes == null) return;
    Navigator.of(context).pop<Uint8List>(_capturedBytes);
  }

  void _onCancel() {
    Navigator.of(context).pop<Uint8List?>(null);
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
        _onCancel();
      },
      child: Scaffold(
        backgroundColor: Colors.black,
        body: SafeArea(
          child: Column(
            children: [
              _buildHeader(),
              Expanded(child: _buildBody()),
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
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.close, color: Colors.white),
            onPressed: _onCancel,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.title,
                  style: const TextStyle(
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
        ],
      ),
    );
  }

  Widget _buildBody() {
    return Center(
      child: AspectRatio(
        aspectRatio: 4 / 3,
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: const Color(0xFF111111),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: Colors.white.withValues(alpha: 0.08),
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: _buildPreviewArea(),
        ),
      ),
    );
  }

  Widget _buildPreviewArea() {
    switch (_phase) {
      case _CapturePhase.starting:
        return const _CenteredSpinner(label: 'Starting camera...');
      case _CapturePhase.error:
        return _ErrorPanel(
          message: _errorMessage ?? 'Camera unavailable.',
          onRetry: () {
            setState(() {
              _phase = _CapturePhase.starting;
              _errorMessage = null;
              _statusMessage = 'Restarting...';
            });
            _bootstrap();
          },
        );
      case _CapturePhase.reviewing:
        if (_capturedBytes != null) {
          return Stack(
            fit: StackFit.expand,
            children: [
              Image.memory(
                _capturedBytes!,
                fit: BoxFit.cover,
                gaplessPlayback: true,
              ),
            ],
          );
        }
        return const SizedBox.shrink();
      case _CapturePhase.capturing:
      case _CapturePhase.previewing:
        return Stack(
          fit: StackFit.expand,
          children: [
            if (_previewBytes != null)
              Image.memory(
                _previewBytes!,
                fit: BoxFit.cover,
                gaplessPlayback: true,
              )
            else
              const _CenteredSpinner(label: 'Waiting for first frame...'),
            const _FramingGuide(),
            if (_phase == _CapturePhase.capturing)
              Container(
                color: Colors.black.withValues(alpha: 0.4),
                alignment: Alignment.center,
                child: const _CenteredSpinner(label: 'Capturing...'),
              ),
          ],
        );
    }
  }

  Widget _buildControls() {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      child: switch (_phase) {
        _CapturePhase.reviewing => _buildReviewControls(),
        _CapturePhase.error => _buildErrorControls(),
        _ => _buildShutterControls(),
      },
    );
  }

  Widget _buildShutterControls() {
    final enabled = _phase == _CapturePhase.previewing && _previewBytes != null;
    return Column(
      children: [
        Text(
          widget.hint,
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.6),
            fontSize: 13,
          ),
        ),
        const SizedBox(height: 16),
        GestureDetector(
          onTap: enabled ? _onShutter : null,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 150),
            width: 76,
            height: 76,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: enabled ? Colors.white : Colors.white38,
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.3),
                width: 4,
              ),
            ),
            child: Center(
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: enabled ? MalaikaColors.primary : Colors.grey,
                ),
                child: const Icon(
                  Icons.camera_alt,
                  color: Colors.white,
                  size: 26,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildReviewControls() {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton.icon(
            onPressed: _onRetake,
            icon: const Icon(Icons.refresh),
            label: const Text('Retake'),
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.white,
              side: BorderSide(color: Colors.white.withValues(alpha: 0.5)),
              padding: const EdgeInsets.symmetric(vertical: 14),
            ),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: ElevatedButton.icon(
            onPressed: _onUse,
            icon: const Icon(Icons.check),
            label: const Text('Use this photo'),
            style: ElevatedButton.styleFrom(
              backgroundColor: MalaikaColors.primary,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 14),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildErrorControls() {
    return Row(
      children: [
        Expanded(
          child: OutlinedButton(
            onPressed: _onCancel,
            style: OutlinedButton.styleFrom(
              foregroundColor: Colors.white,
              side: BorderSide(color: Colors.white.withValues(alpha: 0.5)),
              padding: const EdgeInsets.symmetric(vertical: 14),
            ),
            child: const Text('Cancel'),
          ),
        ),
      ],
    );
  }
}

class _CenteredSpinner extends StatelessWidget {
  final String label;
  const _CenteredSpinner({required this.label});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox(
            width: 28,
            height: 28,
            child: CircularProgressIndicator(
              strokeWidth: 2.5,
              color: Colors.white,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            label,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.8),
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }
}

class _FramingGuide extends StatelessWidget {
  const _FramingGuide();

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Center(
        child: FractionallySizedBox(
          widthFactor: 0.7,
          heightFactor: 0.85,
          child: DecoratedBox(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(140),
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.55),
                width: 2,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ErrorPanel extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorPanel({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, color: Colors.white70, size: 48),
            const SizedBox(height: 12),
            Text(
              message,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white70, fontSize: 14),
            ),
            const SizedBox(height: 20),
            OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh, color: Colors.white),
              label: const Text(
                'Retry',
                style: TextStyle(color: Colors.white),
              ),
              style: OutlinedButton.styleFrom(
                side: BorderSide(color: Colors.white.withValues(alpha: 0.5)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
