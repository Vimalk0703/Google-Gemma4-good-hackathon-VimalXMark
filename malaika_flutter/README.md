# Malaika — Flutter app (Tier 0)

The **Tier 0** surface of Malaika: a fully-offline Android app that runs Google's **Gemma 4 E2B** model directly on the device and walks a caregiver through the WHO Integrated Management of Childhood Illness (IMCI) protocol.

This is the **primary demo** for the Gemma 4 Good Hackathon. The phone *is* the product.

> Read [`../CLAUDE.md`](../CLAUDE.md) and [`../AGENTS.md`](../AGENTS.md) before contributing. The project's absolute rules apply here.

---

## What it does

| Feature | Status |
|---|---|
| Text-based IMCI Q&A (~20 structured questions) | works |
| Gemma 4 narrates each question naturally to the caregiver | works |
| Photo from gallery → on-device vision analysis (alertness, dehydration, wasting, oedema) | works |
| Q&A vs vision reconciliation engine | works |
| Deterministic WHO IMCI classification (`SEVERE` / `MODERATE` / `MILD`) | works |
| Final report with severity + treatment actions | works |
| Offline voice input/output (Android native STT + TTS, CPU only) | works |
| Fully offline — no internet at any point | works |
| In-app camera preview | **not supported** — Mali GPU has no headroom while Gemma 4 is loaded |
| System-camera capture | **not supported** — Android OOM-kills the app on background |
| Video processing / breath-rate detection | **not supported** — Tier 1 only |
| Audio breath-sound classification | **not supported** — Tier 1 (clinic GPU) only |
| Real-time continuous monitoring | **not supported** — single-photo assessment |

The "not supported" rows are intentional. Tier 1 (Python on a clinic GPU) handles them; this tier prioritises robustness on $60 hardware over feature breadth.

---

## Hardware reality

Tested on **Samsung Galaxy A53** (Mali G68 MC4 GPU, 6 GB RAM, Android 14).

- Gemma 4 E2B uses ~2.3 GB of the ~2.5 GB usable GPU memory.
- A camera preview surface crashes the GPU driver — there is no headroom.
- The gallery image picker works because it runs in-process and allocates no GPU.
- Speech-to-text and text-to-speech run on the CPU via Android native engines; they don't conflict with the model.
- A fresh LLM session is created per inference to prevent KV-cache accumulation crashes.

These constraints are not bugs. They are the design.

---

## Build and run

### Prerequisites

- Flutter `>=3.24.0`
- Dart `>=3.5.0`
- Android SDK 34+
- An Android device or emulator with at least 4 GB RAM (real device strongly recommended; the emulator's GPU layer doesn't represent real-world memory)

### First run

```bash
flutter pub get
flutter analyze              # lint
flutter test                 # unit tests
flutter build apk --debug    # debug APK in build/app/outputs/flutter-apk/
flutter install              # install to connected device
```

### Model download

On first launch, the splash screen downloads `Gemma 4 E2B` (~2.6 GB) over Wi-Fi and caches it locally. After that, the app works fully offline.

If you prefer to side-load the model, drop the `.task` file into the device's app data directory (the path is logged on first launch).

---

## Architecture

```
lib/
├── screens/
│   ├── splash_screen.dart            # Model download + GPU initialization
│   ├── dashboard_screen.dart         # Main menu
│   ├── home_screen.dart              # IMCI Q&A orchestrator (~970 lines)
│   └── camera_monitor_screen.dart    # Gallery photo picker + vision analysis
├── core/
│   ├── imci_questionnaire.dart       # Structured IMCI questions + answer parsing
│   ├── imci_protocol.dart            # WHO thresholds + deterministic classification
│   ├── imci_types.dart               # Severity / classification enums
│   ├── reconciliation_engine.dart    # Cross-references Q&A vs vision findings
│   └── voice_service.dart            # Offline STT + TTS (Android native CPU engines)
├── theme/
│   └── malaika_theme.dart            # Brand colours + severity palette
├── widgets/
│   ├── chat_bubble.dart
│   ├── imci_progress_bar.dart
│   ├── classification_card.dart
│   └── reasoning_card.dart
└── inference/
    └── model_manager.dart            # Model path management
```

### What Gemma 4 does on the phone

- Rephrases IMCI questions naturally for caregivers
- Parses caregiver responses (any language Gemma 4 supports)
- Analyses photos for alertness, dehydration, wasting, oedema
- Generates a caring summary at the end of the assessment

### What Dart code does

- Manages the IMCI Q&A state machine (`imci_questionnaire.dart`)
- Compares Q&A vs vision findings (`reconciliation_engine.dart`)
- Applies WHO IMCI thresholds (`imci_protocol.dart` — must mirror `malaika/imci_protocol.py` exactly)
- Selects the treatment template based on the deterministic classification

The boundary between LLM perception and deterministic clinical decision-making is sacred. See [`../AGENTS.md`](../AGENTS.md) for details.

---

## Dependencies of note

| Package | Role |
|---|---|
| `flutter_gemma` | On-device Gemma 4 inference via Google's MediaPipe LLM SDK |
| `speech_to_text` | Offline STT via Android's native engine |
| `flutter_tts` | Offline TTS via Android's native engine |
| `image_picker` | Gallery photo picker (no GPU allocation) |
| `image` | Pure-Dart JPEG re-encode (Gemma 4 vision adapter requires JPEG bytes) |
| `permission_handler` | Mic + storage permissions |

Dependencies are auto-bumped weekly by Dependabot — see [`../.github/dependabot.yml`](../.github/dependabot.yml).

---

## Testing

```bash
flutter analyze              # lint, must be clean
flutter test                 # unit tests
```

Unit tests live alongside `lib/` in the standard Flutter `test/` directory. Integration / on-device tests are run manually on a real Samsung A53 before any release. The phone capability matrix at the top of this README is the source of truth — adding a row requires a real-device test.

---

## Troubleshooting

**App crashes on startup**: model download didn't complete. Delete app data and try again on Wi-Fi. Check log for `flutter_gemma` initialization errors.

**App freezes mid-assessment**: probable KV-cache accumulation. The codebase already creates a fresh LLM session per inference; if this regresses, the bug is in `inference/model_manager.dart`.

**Voice input doesn't work**: confirm microphone permission is granted and that the Android STT engine is installed (settings → languages & input).

**Photo analysis returns garbage**: confirm the photo is JPEG, not PNG. The vision adapter's bindings are JPEG-only at the moment.

**App is OOM-killed when backgrounded**: known limitation. Gemma 4 E2B fully occupies the GPU and Android cannot preserve it across a background. Don't background mid-assessment.

---

## License

Apache 2.0 — see [`../LICENSE`](../LICENSE).
