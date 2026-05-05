package com.malaika.malaika_flutter

import android.app.Activity
import android.content.Context
import android.graphics.ImageFormat
import android.hardware.camera2.CameraCaptureSession
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraDevice
import android.hardware.camera2.CameraManager
import android.hardware.camera2.CaptureRequest
import android.hardware.camera2.TotalCaptureResult
import android.hardware.camera2.params.StreamConfigurationMap
import android.media.ImageReader
import android.os.Handler
import android.os.HandlerThread
import android.util.Log
import android.util.Range
import android.util.Size
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.util.concurrent.atomic.AtomicReference

/**
 * Headless Camera2 plugin — minimum-memory variant.
 *
 * Memory pressure on the A53 with Gemma 4 E2B loaded (~2.3GB RSS) means the
 * Linux Low Memory Killer reclaims us when the camera HAL spins up. To
 * survive LMKD we use a SINGLE ImageReader (not two) at modest resolution,
 * maxImages=1, throttled to 2-5 fps via TARGET_FPS_RANGE.
 *
 * Preview vs capture differ only by JPEG_QUALITY and a `pendingCapture` flag
 * inside the listener. Before firing a high-quality still we stop the
 * repeating request and drain the reader to ensure the next frame the
 * listener delivers is the high-quality capture, not a leftover preview.
 */
class MalaikaCameraPlugin(
    private val activity: Activity,
    messenger: BinaryMessenger,
) : MethodChannel.MethodCallHandler {

    companion object {
        private const val TAG = "MalaikaCamera"
        private const val CHANNEL = "malaika.camera"
        private const val IMAGE_WIDTH_DEFAULT = 640
        private const val IMAGE_HEIGHT_DEFAULT = 480
        private const val PREVIEW_QUALITY: Byte = 50
        private const val CAPTURE_QUALITY: Byte = 90
    }

    private val channel = MethodChannel(messenger, CHANNEL).also {
        it.setMethodCallHandler(this)
    }
    private val cameraManager =
        activity.getSystemService(Context.CAMERA_SERVICE) as CameraManager

    private var backgroundThread: HandlerThread? = null
    private var backgroundHandler: Handler? = null
    private var cameraDevice: CameraDevice? = null
    private var captureSession: CameraCaptureSession? = null
    private var imageReader: ImageReader? = null
    private var cameraId: String? = null
    private var previewBuilder: CaptureRequest.Builder? = null

    private val latestPreviewJpeg = AtomicReference<ByteArray?>(null)
    @Volatile private var pendingCapture: ((ByteArray?) -> Unit)? = null

    fun dispose() {
        stopInternal()
        channel.setMethodCallHandler(null)
    }

    // ------------------------------------------------------------------------
    // MethodChannel entrypoint
    // ------------------------------------------------------------------------

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "start" -> {
                val w = call.argument<Int>("captureWidth") ?: IMAGE_WIDTH_DEFAULT
                val h = call.argument<Int>("captureHeight") ?: IMAGE_HEIGHT_DEFAULT
                start(w, h, result)
            }
            "pullFrame" -> result.success(latestPreviewJpeg.get())
            "capture" -> capture(result)
            "stop" -> {
                stopInternal()
                result.success(true)
            }
            else -> result.notImplemented()
        }
    }

    // ------------------------------------------------------------------------
    // Lifecycle
    // ------------------------------------------------------------------------

    private fun start(targetWidth: Int, targetHeight: Int, result: MethodChannel.Result) {
        try {
            startBackgroundThread()
            val id = pickBackCamera()
            if (id == null) {
                result.error("NO_CAMERA", "No back-facing camera found", null)
                return
            }
            cameraId = id

            val characteristics = cameraManager.getCameraCharacteristics(id)
            val map = characteristics.get(
                CameraCharacteristics.SCALER_STREAM_CONFIGURATION_MAP
            ) as StreamConfigurationMap
            val size = chooseSize(map, targetWidth, targetHeight)
            Log.i(TAG, "Image size chosen: ${size.width}x${size.height}")

            imageReader = ImageReader.newInstance(
                size.width, size.height, ImageFormat.JPEG, 1
            ).apply {
                setOnImageAvailableListener({ reader ->
                    val image = reader.acquireLatestImage() ?: return@setOnImageAvailableListener
                    try {
                        val buffer = image.planes[0].buffer
                        val bytes = ByteArray(buffer.remaining())
                        buffer.get(bytes)

                        val cb = pendingCapture
                        if (cb != null) {
                            pendingCapture = null
                            cb.invoke(bytes)
                        } else {
                            latestPreviewJpeg.set(bytes)
                        }
                    } finally {
                        image.close()
                    }
                }, backgroundHandler)
            }

            openCamera(id, result)
        } catch (e: SecurityException) {
            result.error("PERMISSION", "CAMERA permission denied", e.message)
        } catch (e: Throwable) {
            Log.e(TAG, "start failed", e)
            stopInternal()
            result.error("START_FAILED", e.message, null)
        }
    }

    private fun openCamera(id: String, result: MethodChannel.Result) {
        cameraManager.openCamera(id, object : CameraDevice.StateCallback() {
            override fun onOpened(device: CameraDevice) {
                cameraDevice = device
                createSession(result)
            }

            override fun onDisconnected(device: CameraDevice) {
                Log.w(TAG, "Camera disconnected")
                device.close()
                cameraDevice = null
            }

            override fun onError(device: CameraDevice, error: Int) {
                Log.e(TAG, "Camera error code=$error")
                device.close()
                cameraDevice = null
                result.error("CAMERA_ERROR", "Camera error $error", null)
            }
        }, backgroundHandler)
    }

    private fun createSession(result: MethodChannel.Result) {
        val device = cameraDevice ?: run {
            result.error("NO_DEVICE", "Camera device null after open", null)
            return
        }
        val surface = imageReader?.surface ?: run {
            result.error("NO_SURFACE", "ImageReader surface null", null)
            return
        }

        @Suppress("DEPRECATION")
        device.createCaptureSession(
            listOf(surface),
            object : CameraCaptureSession.StateCallback() {
                override fun onConfigured(session: CameraCaptureSession) {
                    captureSession = session
                    try {
                        val builder = device.createCaptureRequest(
                            CameraDevice.TEMPLATE_PREVIEW
                        ).apply {
                            addTarget(surface)
                            set(
                                CaptureRequest.CONTROL_AF_MODE,
                                CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE
                            )
                            set(
                                CaptureRequest.CONTROL_AE_MODE,
                                CaptureRequest.CONTROL_AE_MODE_ON
                            )
                            set(
                                CaptureRequest.CONTROL_AE_TARGET_FPS_RANGE,
                                Range(2, 5)
                            )
                            set(CaptureRequest.JPEG_QUALITY, PREVIEW_QUALITY)
                        }
                        previewBuilder = builder
                        session.setRepeatingRequest(builder.build(), null, backgroundHandler)
                        result.success(true)
                    } catch (e: Throwable) {
                        Log.e(TAG, "setRepeatingRequest failed", e)
                        result.error("REPEATING_FAILED", e.message, null)
                    }
                }

                override fun onConfigureFailed(session: CameraCaptureSession) {
                    Log.e(TAG, "Session configure failed")
                    result.error("SESSION_FAILED", "createCaptureSession failed", null)
                }
            },
            backgroundHandler
        )
    }

    // ------------------------------------------------------------------------
    // High-quality capture
    // ------------------------------------------------------------------------

    private fun capture(result: MethodChannel.Result) {
        val device = cameraDevice
        val session = captureSession
        val reader = imageReader
        val surface = reader?.surface
        if (device == null || session == null || surface == null) {
            result.error("NOT_STARTED", "Camera not started", null)
            return
        }
        if (pendingCapture != null) {
            result.error("BUSY", "Previous capture still in flight", null)
            return
        }

        try {
            // Drain any leftover preview frames so the listener delivers
            // the high-quality still next.
            session.stopRepeating()
            drainReader(reader)

            pendingCapture = { bytes ->
                activity.runOnUiThread {
                    if (bytes != null && bytes.isNotEmpty()) {
                        result.success(bytes)
                    } else {
                        result.error("CAPTURE_NULL", "ImageReader produced no image", null)
                    }
                }
                resumePreview()
            }

            val builder = device.createCaptureRequest(
                CameraDevice.TEMPLATE_STILL_CAPTURE
            ).apply {
                addTarget(surface)
                set(
                    CaptureRequest.CONTROL_AF_MODE,
                    CaptureRequest.CONTROL_AF_MODE_CONTINUOUS_PICTURE
                )
                set(
                    CaptureRequest.CONTROL_AE_MODE,
                    CaptureRequest.CONTROL_AE_MODE_ON
                )
                set(CaptureRequest.JPEG_QUALITY, CAPTURE_QUALITY)
                set(
                    CaptureRequest.JPEG_ORIENTATION,
                    sensorOrientation()
                )
            }

            session.capture(
                builder.build(),
                object : CameraCaptureSession.CaptureCallback() {
                    override fun onCaptureFailed(
                        session: CameraCaptureSession,
                        request: CaptureRequest,
                        failure: android.hardware.camera2.CaptureFailure,
                    ) {
                        Log.e(TAG, "Capture failed reason=${failure.reason}")
                        val cb = pendingCapture
                        pendingCapture = null
                        activity.runOnUiThread {
                            cb?.invoke(null) ?: result.error(
                                "CAPTURE_FAILED",
                                "reason=${failure.reason}",
                                null
                            )
                        }
                        resumePreview()
                    }

                    override fun onCaptureCompleted(
                        session: CameraCaptureSession,
                        request: CaptureRequest,
                        result: TotalCaptureResult,
                    ) {
                        // ImageReader listener delivers JPEG; resume happens there.
                    }
                },
                backgroundHandler
            )
        } catch (e: Throwable) {
            Log.e(TAG, "capture failed", e)
            pendingCapture = null
            resumePreview()
            result.error("CAPTURE_EXCEPTION", e.message, null)
        }
    }

    private fun resumePreview() {
        val session = captureSession ?: return
        val builder = previewBuilder ?: return
        try {
            session.setRepeatingRequest(builder.build(), null, backgroundHandler)
        } catch (e: Throwable) {
            Log.w(TAG, "resumePreview failed", e)
        }
    }

    private fun drainReader(reader: ImageReader) {
        while (true) {
            val img = try {
                reader.acquireLatestImage()
            } catch (_: Throwable) {
                null
            } ?: return
            try {
                img.close()
            } catch (_: Throwable) {}
        }
    }

    // ------------------------------------------------------------------------
    // Teardown
    // ------------------------------------------------------------------------

    private fun stopInternal() {
        try {
            captureSession?.close()
        } catch (_: Throwable) {}
        captureSession = null
        try {
            cameraDevice?.close()
        } catch (_: Throwable) {}
        cameraDevice = null
        try {
            imageReader?.close()
        } catch (_: Throwable) {}
        imageReader = null
        previewBuilder = null
        latestPreviewJpeg.set(null)
        pendingCapture = null
        stopBackgroundThread()
    }

    private fun startBackgroundThread() {
        if (backgroundThread != null) return
        backgroundThread = HandlerThread("MalaikaCameraBg").apply { start() }
        backgroundHandler = Handler(backgroundThread!!.looper)
    }

    private fun stopBackgroundThread() {
        backgroundThread?.quitSafely()
        try {
            backgroundThread?.join(500)
        } catch (_: InterruptedException) {}
        backgroundThread = null
        backgroundHandler = null
    }

    // ------------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------------

    private fun pickBackCamera(): String? {
        for (id in cameraManager.cameraIdList) {
            val facing = cameraManager.getCameraCharacteristics(id)
                .get(CameraCharacteristics.LENS_FACING)
            if (facing == CameraCharacteristics.LENS_FACING_BACK) return id
        }
        return cameraManager.cameraIdList.firstOrNull()
    }

    /**
     * Pick the SMALLEST supported JPEG size that still covers the requested
     * area. Smaller HAL pipelines mean less memory pressure under LMKD.
     */
    private fun chooseSize(
        map: StreamConfigurationMap,
        targetWidth: Int,
        targetHeight: Int,
    ): Size {
        val sizes = map.getOutputSizes(ImageFormat.JPEG) ?: emptyArray()
        if (sizes.isEmpty()) return Size(targetWidth, targetHeight)

        // First pass: find sizes >= target on both axes; pick the smallest.
        val coverage = sizes.filter {
            it.width >= targetWidth && it.height >= targetHeight
        }.minByOrNull { it.width.toLong() * it.height }
        if (coverage != null) return coverage

        // Fallback: pick the largest available (at least we get something).
        return sizes.maxByOrNull { it.width.toLong() * it.height } ?: sizes[0]
    }

    private fun sensorOrientation(): Int {
        val id = cameraId ?: return 0
        return cameraManager.getCameraCharacteristics(id)
            .get(CameraCharacteristics.SENSOR_ORIENTATION) ?: 0
    }
}
