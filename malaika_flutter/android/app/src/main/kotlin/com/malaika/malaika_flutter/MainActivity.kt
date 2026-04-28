package com.malaika.malaika_flutter

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine

class MainActivity : FlutterActivity() {
    private var cameraPlugin: MalaikaCameraPlugin? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        cameraPlugin = MalaikaCameraPlugin(this, flutterEngine.dartExecutor.binaryMessenger)
    }

    override fun onDestroy() {
        cameraPlugin?.dispose()
        cameraPlugin = null
        super.onDestroy()
    }
}
