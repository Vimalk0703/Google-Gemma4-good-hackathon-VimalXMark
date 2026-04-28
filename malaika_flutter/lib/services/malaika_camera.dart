/// Headless Camera2 bridge — pairs with `MalaikaCameraPlugin.kt`.
///
/// The Mali GPU on the A53 cannot host both Gemma 4 E2B and a SurfaceView
/// camera preview, so this service goes through a native Camera2 plugin that
/// only allocates CPU-readable JPEG buffers (ImageReader). Flutter pulls the
/// latest preview JPEG ~2× per second and renders it via `Image.memory`.
library;

import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';

class MalaikaCamera {
  MalaikaCamera._();

  static final MalaikaCamera instance = MalaikaCamera._();

  static const MethodChannel _channel = MethodChannel('malaika.camera');

  bool _started = false;

  bool get isStarted => _started;

  /// Request CAMERA permission. Returns true if granted.
  Future<bool> requestPermission() async {
    final status = await Permission.camera.request();
    return status.isGranted;
  }

  /// Start the camera. The plugin opens a CaptureSession with a single
  /// ImageReader at the requested size (smallest supported JPEG output that
  /// covers the requested area). No SurfaceView, no GPU surface.
  ///
  /// Defaults are intentionally small (640×480) — A53 Mali memory plus
  /// Gemma 4 E2B (~2.3GB) leaves little headroom; bigger camera buffers
  /// trigger Android's Low Memory Killer.
  Future<bool> start({
    int captureWidth = 640,
    int captureHeight = 480,
  }) async {
    final ok = await _channel.invokeMethod<bool>('start', {
      'captureWidth': captureWidth,
      'captureHeight': captureHeight,
    });
    _started = ok ?? false;
    return _started;
  }

  /// Returns the most recent preview JPEG, or null if none yet.
  Future<Uint8List?> pullFrame() async {
    if (!_started) return null;
    final bytes = await _channel.invokeMethod<Uint8List>('pullFrame');
    return bytes;
  }

  /// Capture a single high-resolution JPEG. Returns null on failure.
  Future<Uint8List?> capture() async {
    if (!_started) return null;
    try {
      final bytes = await _channel.invokeMethod<Uint8List>('capture');
      return bytes;
    } on PlatformException {
      return null;
    }
  }

  /// Stop the camera and release all native resources.
  Future<void> stop() async {
    if (!_started) return;
    try {
      await _channel.invokeMethod<bool>('stop');
    } on PlatformException {
      // ignore — we still want to mark stopped
    }
    _started = false;
  }
}
