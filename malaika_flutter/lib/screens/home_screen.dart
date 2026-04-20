import 'package:flutter/material.dart';
import 'package:flutter_gemma/flutter_gemma.dart';
import 'package:image_picker/image_picker.dart';
import '../theme/malaika_theme.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/imci_progress_bar.dart';
import '../widgets/classification_card.dart';
import '../widgets/reasoning_card.dart';
import '../core/imci_questionnaire.dart';
import '../core/reconciliation_engine.dart';
import '../core/voice_service.dart';
import '../widgets/voice_waveform.dart';
import 'camera_monitor_screen.dart';

/// IMCI assessment using structured Q&A collection + LLM narration.
///
/// Phase 1: COLLECT — Walk through predefined IMCI questions in order.
///   LLM rephrases each question naturally. User answers.
///   Reasoning card shows extracted findings after each answer.
///
/// Phase 2: CLASSIFY — After each step completes, run deterministic WHO
///   classification (imci_protocol.dart). Show classification card.
///
/// Phase 3: NARRATE — After all questions, LLM generates a comprehensive
///   report from all Q&A pairs + classifications.

class HomeScreen extends StatefulWidget {
  final bool modelLoaded;
  const HomeScreen({super.key, this.modelLoaded = false});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

enum VoiceState { idle, listening, thinking, speaking }

class _HomeScreenState extends State<HomeScreen> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<_ChatItem> _chatItems = [];
  VoiceState _voiceState = VoiceState.idle;

  /// Voice service — offline STT + TTS on CPU.
  final VoiceService _voice = VoiceService();
  bool _voiceReady = false;
  bool _voiceMode = false; // Continuous voice — one tap to activate
  String _partialText = '';

  /// The questionnaire manages all IMCI Q&A state.
  final ImciQuestionnaire _q = ImciQuestionnaire();

  /// Progress bar step (0-5).
  int _progressStep = 0;

  /// LLM chat session.
  dynamic _chat;
  String _chatStep = '';

  /// Track the previous step for transition banners.
  String _lastDisplayedStep = 'greeting';

  /// System prompt for the LLM — just persona and tone.
  static const _systemPrompt =
      'You are Malaika, a warm and caring child health assistant. '
      'You help caregivers check on their child\'s health.\n'
      'RULES:\n'
      '- Keep responses to 1-2 short sentences\n'
      '- Be warm and reassuring\n'
      '- ONLY ask the question you are told to ask\n'
      '- Do NOT add extra questions or ask about other topics\n'
      '- Do NOT assume any symptoms\n'
      '- Acknowledge what the caregiver says briefly, then ask the given question\n'
      '- Never diagnose';

  /// Report-specific system prompt (no "only ask questions" rule).
  static const _reportPrompt =
      'You are Malaika, a caring child health assistant. '
      'Generate a clear, practical health report. '
      'Explain findings simply. Be caring but direct. '
      'Never diagnose — recommend seeing a health worker.';

  @override
  void initState() {
    super.initState();
    _startAssessment();
    _initVoice();
  }

  Future<void> _initVoice() async {
    final ok = await _voice.init();
    if (mounted) setState(() => _voiceReady = ok);

    _voice.onResult = _onSttResult;
    _voice.onPartial = (text) {
      if (mounted) setState(() => _partialText = text);
    };
    _voice.onListeningStopped = () {
      if (!mounted) return;
      if (_voiceState == VoiceState.listening) {
        // In voice mode, re-listen after timeout (no speech detected)
        if (_voiceMode) {
          Future.delayed(const Duration(milliseconds: 300), () {
            if (mounted && _voiceMode && _voiceState == VoiceState.listening) {
              _startListening();
            }
          });
        } else {
          setState(() {
            _voiceState = VoiceState.idle;
            _partialText = '';
          });
        }
      }
    };
    _voice.onSpeakingDone = _onSpeakingDone;
    _voice.onError = () {
      if (mounted) {
        setState(() {
          _voiceState = VoiceState.idle;
          _partialText = '';
        });
      }
    };
  }

  void _onSttResult(String recognizedText) {
    if (recognizedText.trim().isEmpty) {
      // Empty result — re-listen if in voice mode
      if (_voiceMode && mounted) {
        _startListening();
      } else if (mounted && _voiceState != VoiceState.speaking) {
        setState(() => _voiceState = VoiceState.idle);
      }
      return;
    }

    _partialText = '';
    _textController.text = recognizedText.trim();
    _sendText();
  }

  void _onSpeakingDone() {
    if (!mounted) return;
    setState(() => _voiceState = VoiceState.idle);
    // In voice mode, auto-listen after every response
    if (_voiceMode && !_q.isComplete) {
      Future.delayed(const Duration(milliseconds: 400), () {
        if (mounted && _voiceState == VoiceState.idle && _voiceMode) {
          _startListening();
        }
      });
    }
  }

  /// Start listening (internal — used by voice mode auto-listen and mic tap).
  Future<void> _startListening() async {
    if (!_voiceReady) return;
    setState(() {
      _voiceState = VoiceState.listening;
      _partialText = '';
    });
    await _voice.startListening();
  }

  Future<void> _onMicTap() async {
    // If voice mode is active and user taps mic, exit voice mode
    if (_voiceMode && _voiceState != VoiceState.idle) {
      await _voice.stopListening();
      await _voice.stopSpeaking();
      setState(() {
        _voiceMode = false;
        _voiceState = VoiceState.idle;
        _partialText = '';
      });
      return;
    }

    switch (_voiceState) {
      case VoiceState.idle:
        if (!_voiceReady) {
          _showVoiceUnavailableSnackbar();
          return;
        }
        // Activate continuous voice mode
        setState(() => _voiceMode = true);
    
        await _startListening();
      case VoiceState.listening:
        await _voice.stopListening();
      case VoiceState.speaking:
        await _voice.stopSpeaking();
        setState(() {
          _voiceMode = false;
          _voiceState = VoiceState.idle;
        });
      case VoiceState.thinking:
        break;
    }
  }

  void _showVoiceUnavailableSnackbar() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text(
          'Offline speech not available. Download an offline language pack '
          'in Settings > Language > Speech.',
        ),
        duration: Duration(seconds: 5),
      ),
    );
  }

  // --------------------------------------------------------------------------
  // LLM Session
  // --------------------------------------------------------------------------

  Future<bool> _initSession(String step, {String? systemPrompt, int maxTokens = 200}) async {
    if (!widget.modelLoaded) return false;
    await _closeChat();
    try {
      final model = await FlutterGemma.getActiveModel(maxTokens: maxTokens);
      _chat = await model.createChat(
        temperature: 0.4,
        topK: 40,
        systemInstruction: systemPrompt ?? _systemPrompt,
      );
      _chatStep = step;
      debugPrint('[MALAIKA] Session: $step');
      return true;
    } catch (e) {
      debugPrint('[MALAIKA] Session error: $e');
      return false;
    }
  }

  Future<void> _closeChat() async {
    if (_chat != null) {
      try {
        await (_chat as dynamic).close();
      } catch (_) {}
      _chat = null;
    }
  }

  Future<String> _ask(String instruction) async {
    if (_chat == null) return '';
    debugPrint('[MALAIKA] Ask: "$instruction"');
    try {
      await _chat!.addQuery(Message(text: instruction, isUser: true));
      final response = await _chat!.generateChatResponse();
      final text = response is TextResponse ? response.token.trim() : '';
      if (text.isNotEmpty && text.length > 5) {
        debugPrint(
            '[MALAIKA] Got (${text.length}): "${text.substring(0, text.length.clamp(0, 100))}"');
        return text;
      }
      // Truncated or empty response — GPU may be under pressure.
      // Close session and retry with a fresh one after brief delay.
      debugPrint('[MALAIKA] Short/empty (${text.length}), retrying with fresh session...');
      await _closeChat();
      await Future.delayed(const Duration(milliseconds: 800));
      if (!await _initSession(_chatStep)) return '';
      await _chat!.addQuery(Message(text: instruction, isUser: true));
      final retry = await _chat!.generateChatResponse();
      return retry is TextResponse ? retry.token.trim() : '';
    } catch (e) {
      debugPrint('[MALAIKA] Error: $e');
      return '';
    }
  }

  // --------------------------------------------------------------------------
  // Assessment Start
  // --------------------------------------------------------------------------

  Future<void> _startAssessment() async {
    setState(() => _voiceState = VoiceState.thinking);
    _addTyping();

    if (await _initSession('greeting')) {
      final greeting = await _ask(
        'Greet the caregiver warmly and ask: ${_q.currentQuestion!.question}',
      );
      _removeTyping();
      _addBot(greeting.isNotEmpty
          ? greeting
          : 'Hello! I am Malaika. ${_q.currentQuestion!.question}');
    } else {
      _removeTyping();
      _addBot('Hello! I am Malaika, your child health assistant. '
          '${_q.currentQuestion!.question}');
    }

    if (mounted && _voiceState != VoiceState.speaking) setState(() => _voiceState = VoiceState.idle);
  }

  // --------------------------------------------------------------------------
  // Main Send — Q&A Collection with Reasoning
  // --------------------------------------------------------------------------

  Future<void> _sendText() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    _textController.clear();
    FocusScope.of(context).unfocus();
    _addUser(text);
    setState(() => _voiceState = VoiceState.thinking);

    // Handle "skip" for photo questions
    if (_q.currentQuestion?.type == AnswerType.photo &&
        (text.toLowerCase() == 'skip' ||
            text.toLowerCase() == 'no photo')) {
      await _onSkipPhoto();
      if (mounted && _voiceState != VoiceState.speaking) setState(() => _voiceState = VoiceState.idle);
      return;
    }

    // If assessment is already complete, handle follow-up
    if (_q.isComplete) {
      _addTyping();
      final response = await _ask(
        'Caregiver asks: "$text". Answer briefly. Remind them to see a health worker.',
      );
      _removeTyping();
      _addBot(response.isNotEmpty
          ? response
          : 'Please show the results to a health worker.');
      if (mounted && _voiceState != VoiceState.speaking) setState(() => _voiceState = VoiceState.idle);
      return;
    }

    // --- REASONING: Snapshot before recording ---
    final currentQ = _q.currentQuestion!;
    final prevRawKeys = Set<String>.from(_q.rawAnswers.keys);
    final prevStep = _q.currentStep;

    // Record the answer and check if a step completed
    final completedStep = _q.recordAnswer(text);

    // --- REASONING: Compute what was extracted ---
    final newKeys = _q.rawAnswers.keys
        .where((k) => !prevRawKeys.contains(k))
        .toList();
    final directKey = currentQ.id;
    final autoFilledKeys =
        newKeys.where((k) => k != directKey).toList();

    // Build findings map for reasoning card
    final reasoningFindings = <String, dynamic>{};
    for (final key in newKeys) {
      reasoningFindings[key] = _q.findings[key];
    }

    debugPrint(
        '[MALAIKA] Extracted: $reasoningFindings (auto: $autoFilledKeys)');

    // Show reasoning card if findings were extracted
    if (reasoningFindings.isNotEmpty) {
      _chatItems.add(_ChatItem(
        type: _ChatItemType.reasoning,
        metadata: {
          'findings': reasoningFindings,
          'autoFilled': autoFilledKeys,
          'stepName': _formatStep(prevStep),
          'stepIndex': _q.stepProgress,
        },
      ));
      setState(() {});
    }

    // If a step just completed, classify and show card
    if (completedStep != null && completedStep != 'greeting') {
      _classifyAndShowCard(completedStep);
    }

    // Step transition banner
    final nextStepName = _q.currentStep;
    if (nextStepName != _lastDisplayedStep &&
        nextStepName != 'complete' &&
        nextStepName != 'greeting') {
      _addStepBanner(nextStepName);
      _lastDisplayedStep = nextStepName;
    }

    // Update progress
    _progressStep = _q.stepProgress;

    // Check if all questions are done
    if (_q.isComplete) {
      await _generateFinalReport();
      if (mounted && _voiceState != VoiceState.speaking) setState(() => _voiceState = VoiceState.idle);
      return;
    }

    // Get the next question
    final nextQ = _q.currentQuestion!;

    // If next question is a photo, handle it specially
    if (nextQ.type == AnswerType.photo) {
      await _handlePhotoQuestion(nextQ, text);
      if (mounted && _voiceState != VoiceState.speaking) setState(() => _voiceState = VoiceState.idle);
      return;
    }

    // ALWAYS create a fresh session for each inference call.
    // Reusing sessions accumulates KV cache on the Mali GPU, which causes
    // native memory corruption (Scudo ERROR) after ~10 turns.
    await _initSession(nextQ.step);

    // Ask the next question via LLM
    _addTyping();
    final prompt = completedStep != null
        ? 'Ask the caregiver: ${nextQ.question}'
        : 'Caregiver said: "$text". Acknowledge briefly, then ask: ${nextQ.question}';
    final response = await _ask(prompt);
    _removeTyping();
    // If LLM didn't include a question, just show the raw question instead.
    if (response.isEmpty || !response.contains('?')) {
      _addBot(nextQ.question);
    } else {
      _addBot(response);
    }

    if (mounted && _voiceState != VoiceState.speaking) setState(() => _voiceState = VoiceState.idle);
  }

  // --------------------------------------------------------------------------
  // Photo Question — vision analysis with targeted clinical prompt
  // --------------------------------------------------------------------------

  Future<void> _handlePhotoQuestion(
      ImciQuestion q, String previousAnswer) async {
    final vp = _q.currentVisionPrompt;
    if (vp == null) {
      _q.skipPhoto();
      return;
    }

    await _initSession(q.step);
    _addTyping();
    final askResponse = await _ask(
      'Caregiver said: "$previousAnswer". Acknowledge briefly, then say: ${vp.askText} '
      'Also mention they can type "skip" if they don\'t have a camera.',
    );
    _removeTyping();
    _addBot(askResponse.isNotEmpty ? askResponse : vp.askText);

    _chatItems.add(_ChatItem(
      type: _ChatItemType.photoPrompt,
      metadata: {'step': q.step, 'label': q.label},
    ));
    if (_voiceState != VoiceState.speaking) setState(() => _voiceState = VoiceState.idle);
  }

  Future<void> _onTakePhoto() async {
    final vp = _q.currentVisionPrompt;
    if (vp == null) return;

    setState(() => _voiceState = VoiceState.thinking);

    try {
      await _closeChat();
      final picker = ImagePicker();
      final image = await picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 256,
        maxHeight: 256,
        imageQuality: 50,
      );

      if (image == null) {
        if (mounted && _voiceState != VoiceState.speaking) setState(() => _voiceState = VoiceState.idle);
        return;
      }

      final imageBytes = await image.readAsBytes();
      _addBot('Analyzing the photo...');

      await _closeChat();
      final model = await FlutterGemma.getActiveModel(
        maxTokens: 200,
        supportImage: true,
        maxNumImages: 1,
      );
      _chat = await model.createChat(
        temperature: 0.2,
        topK: 40,
        supportImage: true,
        systemInstruction:
            'You are a clinical health assistant. '
            'Analyze the image with the specific checklist given. '
            'Be precise and only report what you can see.',
      );
      _chatStep = 'vision';

      await _chat!.addQuery(Message(
        text: vp.analysisPrompt,
        isUser: true,
        imageBytes: imageBytes,
      ));

      final response = await _chat!.generateChatResponse();
      final analysisText =
          response is TextResponse ? response.token.trim() : '';

      if (analysisText.isNotEmpty) {
        debugPrint('[MALAIKA] Vision analysis: $analysisText');
        _q.recordVisionAnalysis(analysisText);
        _addBot('Photo analysis: $analysisText');
      } else {
        debugPrint('[MALAIKA] Vision empty, skipping');
        _q.skipPhoto();
        _addBot(
            'I couldn\'t analyze the photo clearly. Let me continue with questions.');
      }
    } catch (e) {
      debugPrint('[MALAIKA] Vision error: $e');
      _q.skipPhoto();
      _addBot(
          'I had trouble with the photo. Let me continue with questions.');
    }

    _progressStep = _q.stepProgress;

    if (_q.isComplete) {
      await _generateFinalReport();
    } else {
      final nextQ = _q.currentQuestion!;
      if (nextQ.type == AnswerType.photo) {
        await _handlePhotoQuestion(nextQ, '');
      } else {
        await _initSession(nextQ.step);
        _addTyping();
        final response =
            await _ask('Ask the caregiver: ${nextQ.question}');
        _removeTyping();
        if (response.isEmpty || !response.contains('?')) {
          _addBot(nextQ.question);
        } else {
          _addBot(response);
        }
      }
    }

    if (mounted && _voiceState != VoiceState.speaking) setState(() => _voiceState = VoiceState.idle);
  }

  Future<void> _onSkipPhoto() async {
    final completedStep = _q.skipPhoto();
    if (completedStep != null) {
      _classifyAndShowCard(completedStep);
    }
    _progressStep = _q.stepProgress;

    setState(() => _voiceState = VoiceState.thinking);

    if (_q.isComplete) {
      await _generateFinalReport();
    } else {
      final nextQ = _q.currentQuestion!;
      await _initSession(nextQ.step);
      _addTyping();
      final response =
          await _ask('Ask the caregiver: ${nextQ.question}');
      _removeTyping();
      if (response.isEmpty || !response.contains('?')) {
        _addBot(nextQ.question);
      } else {
        _addBot(response);
      }
    }

    if (mounted && _voiceState != VoiceState.speaking) setState(() => _voiceState = VoiceState.idle);
  }

  // --------------------------------------------------------------------------
  // Classification — deterministic, per step
  // --------------------------------------------------------------------------

  void _classifyAndShowCard(String step) {
    final result = _q.classifyStep(step);
    if (result == null) return;

    final label = result.classification.value
        .replaceAll('_', ' ')
        .split(' ')
        .map((w) =>
            w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');

    _chatItems.add(_ChatItem(
      type: _ChatItemType.classification,
      metadata: {
        'step': _formatStep(step),
        'severity': result.severity.value,
        'label': label,
        'reasoning': result.reasoning,
      },
    ));
    setState(() {});
  }

  // --------------------------------------------------------------------------
  // Vision Monitoring — camera assessment after questionnaire
  // --------------------------------------------------------------------------

  /// Launch camera monitoring and return aggregated vision findings.
  Future<CameraMonitorResult?> _launchVisionMonitoring() async {
    if (!mounted) return null;
    final result = await Navigator.of(context).push<CameraMonitorResult>(
      MaterialPageRoute(
        builder: (context) =>
            CameraMonitorScreen(modelLoaded: widget.modelLoaded),
      ),
    );
    return result;
  }

  /// Reconciliation result stored for the report.
  ReconciliationResult? _reconciliation;

  // --------------------------------------------------------------------------
  // Final Report — LLM narration with vision reconciliation
  // --------------------------------------------------------------------------

  Future<void> _generateFinalReport() async {
    // Show all remaining classification cards
    for (final step in imciSteps) {
      if (!_q.classifications.containsKey(step)) {
        _classifyAndShowCard(step);
      }
    }

    // Q&A severity before vision
    final qaSeverity = _q.overallSeverity;

    // --- Vision Monitoring Phase ---
    _chatItems.add(_ChatItem(
      type: _ChatItemType.stepBanner,
      text: 'Vision Assessment',
      metadata: {'step': 'vision'},
    ));
    setState(() {});
    _scrollToBottom();

    _addBot(
      'The questionnaire is complete. Now let\'s do a visual check. '
      'I\'ll use the camera to look for clinical signs.',
    );

    // CRITICAL: Close the text session so the vision session can be created.
    // The model only supports ONE active session at a time.
    await _closeChat();

    // Let native memory from the text session be reclaimed before vision.
    // Without this delay, the vision prefill OOMs on low-RAM devices (A53).
    await Future.delayed(const Duration(seconds: 1));

    final visionResult = await _launchVisionMonitoring();
    debugPrint('[MALAIKA] Vision returned: ${visionResult?.framesAnalyzed ?? 0} frames, '
        'findings: ${visionResult?.findings.keys.toList() ?? []}');

    if (visionResult != null && visionResult.framesAnalyzed > 0) {
      // Run reconciliation
      _reconciliation = ReconciliationEngine.reconcile(
        qaFindings: _q.findings,
        visionFindings: visionResult.findings,
        qaSeverity: qaSeverity,
      );

      // Show vision findings summary with model's own notes
      _chatItems.add(_ChatItem(
        type: _ChatItemType.visionSummary,
        metadata: {
          'findings': visionResult.findings,
          'framesAnalyzed': visionResult.framesAnalyzed,
          'notes': visionResult.notes,
        },
      ));
      setState(() {});

      // Show warnings if any
      if (_reconciliation!.hasWarnings) {
        for (final warning in _reconciliation!.warnings) {
          _chatItems.add(_ChatItem(
            type: _ChatItemType.reconciliationWarning,
            metadata: {
              'category': warning.category,
              'qaValue': warning.qaValue,
              'visionValue': warning.visionValue,
              'confidence': warning.confidence,
              'message': warning.message,
              'recommendation': warning.recommendation,
              'severity': warning.severity,
            },
          ));
        }
        setState(() {});
      }
    } else {
      _addBot('Vision assessment skipped. Generating report from questionnaire only.');
    }

    // Determine final severity (may be upgraded by vision)
    final finalSeverity = _reconciliation?.severityUpgraded == true
        ? _reconciliation!.upgradedSeverity!
        : qaSeverity;

    // Overall assessment card
    const urgencyMap = {
      'red': 'URGENT: Go to a health facility IMMEDIATELY',
      'yellow': 'See a health worker within 24 hours',
      'green': 'Treat at home with follow-up in 5 days',
    };

    final overallLabel = _reconciliation?.severityUpgraded == true
        ? 'Overall: ${finalSeverity.toUpperCase()} (upgraded by vision)'
        : 'Overall: ${finalSeverity.toUpperCase()}';

    _chatItems.add(_ChatItem(
      type: _ChatItemType.classification,
      metadata: {
        'step': 'Overall Assessment',
        'severity': finalSeverity,
        'label': overallLabel,
        'reasoning': urgencyMap[finalSeverity] ?? 'Consult a health worker',
      },
    ));
    setState(() {});

    // LLM generates caring summary — with hard reset after vision
    _addTyping();
    await _closeChat();
    // Hard reset: re-acquire the model to clear any corrupted native state
    // from vision monitoring (E2B LiteRT can't process images, leaves bad state)
    try {
      await FlutterGemma.getActiveModel(maxTokens: 200, preferredBackend: PreferredBackend.gpu);
    } catch (_) {}
    await Future.delayed(const Duration(milliseconds: 300));
    await _initSession('report', systemPrompt: _reportPrompt, maxTokens: 512);
    final reportContext = _q.buildReportContext();
    // Build detailed vision context for the report prompt.
    var visionContext = '';
    if (_reconciliation != null) {
      final vf = _reconciliation!.visionFindings;
      final visionParts = <String>[];
      for (final entry in vf.entries) {
        final label = entry.key.replaceAll('_', ' ');
        visionParts.add('$label: ${entry.value.detected ? "YES" : "no"}');
      }
      visionContext = ' Photo assessment: ${visionParts.join(", ")}.';
      if (_reconciliation!.hasWarnings) {
        final warnMsgs = _reconciliation!.warnings
            .map((w) => '${w.category}: ${w.message}')
            .join('; ');
        visionContext += ' Warnings: $warnMsgs.';
      }
    }
    var report = await _ask(
      'Write 2-3 short plain-text sentences summarizing the child\'s condition '
      'for a caregiver. No bullet points, no markdown, no asterisks, no formatting. '
      'Just simple caring sentences.\n\n$reportContext$visionContext',
    );
    // If model crashed from vision, retry one more time with fresh session
    if (report.isEmpty) {
      debugPrint('[MALAIKA] Report retry after model reset...');
      await _closeChat();
      await Future.delayed(const Duration(milliseconds: 500));
      try {
        await FlutterGemma.getActiveModel(maxTokens: 200, preferredBackend: PreferredBackend.gpu);
      } catch (_) {}
      if (await _initSession('report', systemPrompt: _reportPrompt, maxTokens: 512)) {
        report = await _ask(
          'Write 2-3 short plain-text sentences summarizing the child\'s condition '
          'for a caregiver. No bullet points, no markdown, no asterisks, no formatting. '
          'Just simple caring sentences.\n\n$reportContext',
        );
      }
    }
    _removeTyping();

    final cleanReport = report
        .replaceAll(RegExp(r'\*+'), '')
        .replaceAll(RegExp(r'#+\s*'), '')
        .replaceAll(RegExp(r'-\s+'), '')
        .trim();

    // Build the structured report card (with reconciliation data)
    _chatItems.add(_ChatItem(
      type: _ChatItemType.report,
      metadata: _buildReportData(cleanReport, finalSeverity: finalSeverity),
    ));
    setState(() {});
    _scrollToBottom();

    _progressStep = imciSteps.length;
    setState(() {});

    // Speak the concluding summary so the caregiver hears the result
    if (cleanReport.isNotEmpty) {
      _addBot(cleanReport);
    } else {
      _addBot('The assessment is complete. Please show these results to a health worker.');
    }
  }

  Map<String, dynamic> _buildReportData(String llmSummary,
      {String? finalSeverity}) {
    final f = _q.findings;
    final severity = finalSeverity ?? _q.overallSeverity;

    // Positive findings
    final concerns = <String>[];
    final clear = <String>[];
    for (final q in imciQuestions) {
      if (q.type != AnswerType.yesNo) continue;
      final val = f[q.id];
      if (val == true) {
        concerns.add(q.label);
      } else if (val == false && q.triggerKey == null) {
        clear.add(q.label);
      }
    }

    // Treatment actions
    final actions = <Map<String, String>>[];
    if (severity == 'red') {
      actions.add({
        'icon': 'hospital',
        'text': 'Go to a health facility IMMEDIATELY',
      });
    } else if (severity == 'yellow') {
      actions.add({
        'icon': 'schedule',
        'text': 'See a health worker within 24 hours',
      });
    } else {
      actions.add({
        'icon': 'home',
        'text': 'Treat at home. Return in 5 days if not better',
      });
    }
    if (f['has_diarrhea'] == true) {
      actions.add({
        'icon': 'water',
        'text': 'Give ORS mixed with clean water — small sips often',
      });
    }
    if (f['has_fever'] == true) {
      actions.add({
        'icon': 'medication',
        'text': 'Give paracetamol if available. Keep child lightly dressed',
      });
    }
    if (f['has_cough'] == true) {
      actions.add({
        'icon': 'air',
        'text': 'Keep child warm. Watch for fast or difficult breathing',
      });
    }
    actions.add({
      'icon': 'breastfeeding',
      'text': 'Continue breastfeeding or giving fluids',
    });
    actions.add({
      'icon': 'warning',
      'text': 'Return IMMEDIATELY if child stops drinking, has seizures, or gets worse',
    });

    return {
      'severity': severity,
      'ageMonths': _q.ageMonths,
      'summary': llmSummary,
      'concerns': concerns,
      'clear': clear,
      'actions': actions,
      'classifications': _q.classifications.entries
          .where((e) => e.value != null)
          .map((e) => {
                'step': _formatStep(e.key),
                'severity': e.value!.severity.value,
                'label': e.value!.classification.value
                    .replaceAll('_', ' ')
                    .split(' ')
                    .map((w) => w.isEmpty
                        ? w
                        : '${w[0].toUpperCase()}${w.substring(1)}')
                    .join(' '),
              })
          .toList(),
    };
  }

  // --------------------------------------------------------------------------
  // UI Helpers
  // --------------------------------------------------------------------------

  void _addBot(String text) {
    setState(
        () => _chatItems.add(_ChatItem(type: _ChatItemType.bot, text: text)));
    _scrollToBottom();
    // Speak the response via TTS
    if (_voice.isTtsEnabled && text.isNotEmpty) {
      setState(() => _voiceState = VoiceState.speaking);
      _voice.speak(text);
    }
  }

  void _addUser(String text) {
    setState(() =>
        _chatItems.add(_ChatItem(type: _ChatItemType.user, text: text)));
    _scrollToBottom();
  }

  void _addTyping() {
    _chatItems.add(_ChatItem(type: _ChatItemType.typing));
    setState(() {});
    _scrollToBottom();
  }

  void _removeTyping() {
    _chatItems.removeWhere((item) => item.type == _ChatItemType.typing);
    setState(() {});
  }

  void _addStepBanner(String step) {
    _chatItems.add(_ChatItem(
      type: _ChatItemType.stepBanner,
      text: _formatStep(step),
      metadata: {'step': step},
    ));
    setState(() {});
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
            _scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut);
      }
    });
  }

  String _formatStep(String step) {
    return step
        .replaceAll('_', ' ')
        .split(' ')
        .map((w) =>
            w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');
  }

  // --------------------------------------------------------------------------
  // Build
  // --------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: const Column(
          children: [
            Text('IMCI Assessment',
                style: TextStyle(
                    fontSize: 16, fontWeight: FontWeight.w600)),
            Text('Powered by Gemma 4',
                style: TextStyle(
                    fontSize: 11, color: MalaikaColors.textMuted)),
          ],
        ),
        actions: [
          // TTS toggle
          IconButton(
            icon: Icon(
              _voice.isTtsEnabled ? Icons.volume_up : Icons.volume_off,
              size: 20,
            ),
            onPressed: () {
              _voice.toggleTts();
              if (!_voice.isTtsEnabled) _voice.stopSpeaking();
              setState(() {});
            },
          ),
          Container(
            margin: const EdgeInsets.only(right: 12),
            padding:
                const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: MalaikaColors.greenLight,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.wifi_off_rounded,
                    size: 12, color: MalaikaColors.green),
                SizedBox(width: 4),
                Text('Offline',
                    style: TextStyle(
                        fontSize: 10,
                        color: MalaikaColors.green,
                        fontWeight: FontWeight.w600)),
              ],
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Progress bar (always visible)
            ImciProgressBar(currentStep: _progressStep),
            // Chat messages
            Expanded(
              child: ListView.builder(
                controller: _scrollController,
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                itemCount: _chatItems.length,
                itemBuilder: (context, index) {
                  final item = _chatItems[index];
                  return switch (item.type) {
                    _ChatItemType.user =>
                      ChatBubble(text: item.text!, isUser: true),
                    _ChatItemType.bot =>
                      ChatBubble(text: item.text!, isUser: false),
                    _ChatItemType.classification => ClassificationCard(
                        step: item.metadata!['step'] as String,
                        severity: item.metadata!['severity'] as String,
                        label: item.metadata!['label'] as String,
                        reasoning:
                            item.metadata!['reasoning'] as String),
                    _ChatItemType.reasoning => ReasoningCard(
                        findings: item.metadata!['findings']
                            as Map<String, dynamic>,
                        autoFilled: (item.metadata!['autoFilled']
                                as List<String>?) ??
                            [],
                        stepName:
                            item.metadata!['stepName'] as String,
                        stepIndex:
                            item.metadata!['stepIndex'] as int),
                    _ChatItemType.stepBanner =>
                      _StepBannerWidget(text: item.text!),
                    _ChatItemType.typing => const _TypingIndicator(),
                    _ChatItemType.report =>
                      _ReportCard(data: item.metadata!),
                    _ChatItemType.photoPrompt => _PhotoPromptCard(
                        label: item.metadata!['label'] as String,
                        onTakePhoto: _onTakePhoto,
                        onSkip: _onSkipPhoto),
                    _ChatItemType.visionSummary =>
                      _VisionSummaryCard(metadata: item.metadata!),
                    _ChatItemType.reconciliationWarning =>
                      _ReconciliationWarningCard(metadata: item.metadata!),
                  };
                },
              ),
            ),
            // Input bar
            _buildInputBar(),
          ],
        ),
      ),
    );
  }

  Widget _buildInputBar() {
    final isThinking = _voiceState == VoiceState.thinking;
    final isListening = _voiceState == VoiceState.listening;
    final isSpeaking = _voiceState == VoiceState.speaking;
    final isBusy = isThinking || isListening;

    return Container(
      padding: EdgeInsets.only(
          left: 16,
          right: 8,
          top: 8,
          bottom: MediaQuery.of(context).padding.bottom + 8),
      decoration: const BoxDecoration(
        color: MalaikaColors.surface,
        border:
            Border(top: BorderSide(color: MalaikaColors.border)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Voice mode: waveform + partial transcription
          if (_voiceMode) ...[
            VoiceWaveform(state: _voiceState),
            if (_partialText.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 6, bottom: 4),
                child: Text(
                  _partialText,
                  style: const TextStyle(
                    fontSize: 14,
                    color: MalaikaColors.text,
                    fontStyle: FontStyle.italic,
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            const SizedBox(height: 8),
            // Stop voice mode button
            GestureDetector(
              onTap: _onMicTap,
              child: Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: (isListening ? MalaikaColors.green : MalaikaColors.primary)
                      .withOpacity(0.12),
                  border: Border.all(
                    color: isListening ? MalaikaColors.green : MalaikaColors.primary,
                    width: 2,
                  ),
                ),
                child: Icon(
                  isListening ? Icons.mic : isSpeaking ? Icons.volume_up : Icons.stop,
                  color: isListening ? MalaikaColors.green : MalaikaColors.primary,
                  size: 24,
                ),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              isListening ? 'Tap to stop' : isSpeaking ? '' : 'Tap to end voice',
              style: const TextStyle(fontSize: 10, color: MalaikaColors.textMuted),
            ),
          ] else ...[
            // Text mode: normal input bar
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _textController,
                    enabled: !isBusy,
                    style: const TextStyle(
                        fontSize: 15, color: MalaikaColors.text),
                    decoration: InputDecoration(
                      hintText: isThinking
                          ? 'Malaika is thinking...'
                          : 'Type or tap mic...',
                      isDense: true,
                    ),
                    onSubmitted: (_) => _sendText(),
                  ),
                ),
                const SizedBox(width: 8),
                // Mic button
                _buildMicButton(),
                const SizedBox(width: 4),
                // Send button
                GestureDetector(
                onTap: isBusy ? null : _sendText,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: isBusy
                        ? MalaikaColors.textMuted
                        : MalaikaColors.primary,
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: Icon(
                    isThinking
                        ? Icons.hourglass_top_rounded
                        : Icons.send_rounded,
                    size: 20,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          ], // end else (text mode)
        ],
      ),
    );
  }

  Widget _buildMicButton() {
    final color = switch (_voiceState) {
      VoiceState.idle => _voiceReady ? MalaikaColors.primary : MalaikaColors.textMuted,
      VoiceState.listening => MalaikaColors.green,
      VoiceState.thinking => MalaikaColors.yellow,
      VoiceState.speaking => MalaikaColors.primary,
    };
    final icon = switch (_voiceState) {
      VoiceState.idle || VoiceState.listening => Icons.mic,
      VoiceState.thinking => Icons.hourglass_top,
      VoiceState.speaking => Icons.volume_up,
    };

    return GestureDetector(
      onTap: _onMicTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 44,
        height: 44,
        decoration: BoxDecoration(
          color: color.withOpacity(0.12),
          shape: BoxShape.circle,
          border: Border.all(color: color.withOpacity(0.4), width: 1.5),
        ),
        child: Icon(icon, size: 20, color: color),
      ),
    );
  }

  @override
  void dispose() {
    _voice.dispose();
    _closeChat();
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }
}

// =============================================================================
// Chat Item Types & Data
// =============================================================================

enum _ChatItemType {
  user,
  bot,
  classification,
  reasoning,
  stepBanner,
  typing,
  photoPrompt,
  report,
  visionSummary,
  reconciliationWarning,
}

class _ChatItem {
  final _ChatItemType type;
  final String? text;
  final Map<String, dynamic>? metadata;
  _ChatItem({required this.type, this.text, this.metadata});
}

// =============================================================================
// Inline Widgets
// =============================================================================

/// Step transition banner — shows when moving to a new IMCI section.
class _StepBannerWidget extends StatelessWidget {
  final String text;
  const _StepBannerWidget({required this.text});

  static const _stepIcons = {
    'Danger Signs': Icons.warning_amber_rounded,
    'Breathing': Icons.air_rounded,
    'Diarrhea': Icons.water_drop_rounded,
    'Fever': Icons.thermostat_rounded,
    'Nutrition': Icons.restaurant_rounded,
    'Vision Assessment': Icons.visibility_rounded,
  };

  @override
  Widget build(BuildContext context) {
    final icon = _stepIcons[text] ?? Icons.arrow_forward_rounded;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          Expanded(
              child: Container(
                  height: 1, color: MalaikaColors.primary.withValues(alpha: 0.15))),
          const SizedBox(width: 12),
          Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
            decoration: BoxDecoration(
              color: MalaikaColors.primaryLight,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                  color: MalaikaColors.primary.withValues(alpha: 0.15)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 14, color: MalaikaColors.primary),
                const SizedBox(width: 6),
                Text(
                  text,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: MalaikaColors.primary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
              child: Container(
                  height: 1, color: MalaikaColors.primary.withValues(alpha: 0.15))),
        ],
      ),
    );
  }
}

/// Typing indicator — animated dots while LLM is processing.
class _TypingIndicator extends StatefulWidget {
  const _TypingIndicator();
  @override
  State<_TypingIndicator> createState() => _TypingIndicatorState();
}

class _TypingIndicatorState extends State<_TypingIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 30,
            height: 30,
            margin: const EdgeInsets.only(top: 2),
            decoration: BoxDecoration(
              color: MalaikaColors.primaryLight,
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.favorite_rounded,
                size: 15, color: MalaikaColors.primary),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(
                horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: MalaikaColors.botBubble,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(18),
                topRight: Radius.circular(18),
                bottomLeft: Radius.circular(4),
                bottomRight: Radius.circular(18),
              ),
            ),
            child: AnimatedBuilder(
              animation: _controller,
              builder: (context, _) {
                return Row(
                  mainAxisSize: MainAxisSize.min,
                  children: List.generate(3, (i) {
                    final delay = i * 0.2;
                    final t = (_controller.value + delay) % 1.0;
                    final opacity = (1.0 - (t - 0.5).abs() * 2)
                        .clamp(0.3, 1.0);
                    return Padding(
                      padding:
                          const EdgeInsets.symmetric(horizontal: 2),
                      child: Opacity(
                        opacity: opacity,
                        child: Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color: MalaikaColors.textMuted,
                            shape: BoxShape.circle,
                          ),
                        ),
                      ),
                    );
                  }),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// Photo prompt card.
class _PhotoPromptCard extends StatelessWidget {
  final String label;
  final VoidCallback onTakePhoto;
  final VoidCallback onSkip;
  const _PhotoPromptCard(
      {required this.label,
      required this.onTakePhoto,
      required this.onSkip});

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.symmetric(vertical: 6),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: MalaikaColors.primaryLight,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
              color: MalaikaColors.primary.withValues(alpha: 0.15)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label,
                style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: MalaikaColors.primary)),
            const SizedBox(height: 10),
            Row(children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: onTakePhoto,
                  icon: const Icon(Icons.photo_library_rounded, size: 18),
                  label: const Text('Choose Photo'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: MalaikaColors.primary,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10)),
                    elevation: 0,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              TextButton(
                onPressed: onSkip,
                child: Text('Skip',
                    style: TextStyle(color: MalaikaColors.textMuted)),
              ),
            ]),
          ],
        ),
      );
}

// =============================================================================
// Final Report Card — structured, interactive, no markdown
// =============================================================================

class _ReportCard extends StatelessWidget {
  final Map<String, dynamic> data;
  const _ReportCard({required this.data});

  static const _actionIcons = {
    'hospital': Icons.local_hospital_rounded,
    'schedule': Icons.schedule_rounded,
    'home': Icons.home_rounded,
    'water': Icons.water_drop_rounded,
    'medication': Icons.medication_rounded,
    'air': Icons.air_rounded,
    'breastfeeding': Icons.child_care_rounded,
    'warning': Icons.warning_amber_rounded,
  };

  @override
  Widget build(BuildContext context) {
    final severity = data['severity'] as String;
    final ageMonths = data['ageMonths'] as int;
    final summary = data['summary'] as String? ?? '';
    final concerns = (data['concerns'] as List<dynamic>?) ?? [];
    final clear = (data['clear'] as List<dynamic>?) ?? [];
    final actions = (data['actions'] as List<dynamic>?) ?? [];
    final classifications =
        (data['classifications'] as List<dynamic>?) ?? [];

    final sevColor = MalaikaColors.forSeverity(severity);
    final sevBg = MalaikaColors.forSeverityBackground(severity);
    final sevIcon = MalaikaColors.severityIcon(severity);
    final sevLabel = MalaikaColors.severityLabel(severity);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Container(
        decoration: BoxDecoration(
          color: MalaikaColors.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: MalaikaColors.border),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.04),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header with severity ──
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: sevBg,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(20),
                  topRight: Radius.circular(20),
                ),
              ),
              child: Column(
                children: [
                  Icon(sevIcon, size: 36, color: sevColor),
                  const SizedBox(height: 8),
                  Text(
                    'Assessment Complete',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: MalaikaColors.text,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 5),
                    decoration: BoxDecoration(
                      color: sevColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      sevLabel,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                        color: sevColor,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Child: $ageMonths months old',
                    style: const TextStyle(
                        fontSize: 12,
                        color: MalaikaColors.textSecondary),
                  ),
                ],
              ),
            ),

            // ── Gemma Summary ──
            if (summary.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                child: Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: MalaikaColors.primaryLight
                        .withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        children: [
                          Icon(Icons.psychology_rounded,
                              size: 14, color: MalaikaColors.primary),
                          SizedBox(width: 6),
                          Text(
                            'Gemma Summary',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: MalaikaColors.primary,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        summary,
                        style: const TextStyle(
                          fontSize: 14,
                          color: MalaikaColors.text,
                          height: 1.5,
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            // ── Classifications Grid ──
            if (classifications.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Classifications',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: MalaikaColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: classifications.map((c) {
                        final m = c as Map<String, dynamic>;
                        final s = m['severity'] as String;
                        final col = MalaikaColors.forSeverity(s);
                        return Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 10, vertical: 6),
                          decoration: BoxDecoration(
                            color:
                                MalaikaColors.forSeverityBackground(s),
                            borderRadius: BorderRadius.circular(10),
                            border: Border.all(
                                color: col.withValues(alpha: 0.2)),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(MalaikaColors.severityIcon(s),
                                  size: 12, color: col),
                              const SizedBox(width: 5),
                              Text(
                                m['step'] as String,
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: col,
                                ),
                              ),
                            ],
                          ),
                        );
                      }).toList(),
                    ),
                  ],
                ),
              ),

            // ── Findings ──
            if (concerns.isNotEmpty || clear.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Findings',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: MalaikaColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      spacing: 6,
                      runSpacing: 6,
                      children: [
                        ...concerns.map((c) => _findingPill(
                            c as String, true)),
                        ...clear.map((c) => _findingPill(
                            c as String, false)),
                      ],
                    ),
                  ],
                ),
              ),

            // ── What To Do ──
            if (actions.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'What To Do',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: MalaikaColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    ...actions.asMap().entries.map((entry) {
                      final a = entry.value as Map<String, dynamic>;
                      final iconKey = a['icon'] as String;
                      final icon = _actionIcons[iconKey] ??
                          Icons.arrow_forward_rounded;
                      final isUrgent = iconKey == 'hospital' ||
                          iconKey == 'warning';
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          crossAxisAlignment:
                              CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 28,
                              height: 28,
                              decoration: BoxDecoration(
                                color: isUrgent
                                    ? MalaikaColors.redLight
                                    : MalaikaColors.surfaceAlt,
                                borderRadius:
                                    BorderRadius.circular(8),
                              ),
                              child: Icon(icon,
                                  size: 14,
                                  color: isUrgent
                                      ? MalaikaColors.red
                                      : MalaikaColors.primary),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                a['text'] as String,
                                style: TextStyle(
                                  fontSize: 13,
                                  color: isUrgent
                                      ? MalaikaColors.red
                                      : MalaikaColors.text,
                                  fontWeight: isUrgent
                                      ? FontWeight.w600
                                      : FontWeight.normal,
                                  height: 1.4,
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    }),
                  ],
                ),
              ),

            // ── Footer ──
            Padding(
              padding: const EdgeInsets.all(20),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: MalaikaColors.surfaceAlt,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: const Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.verified_rounded,
                            size: 12, color: MalaikaColors.textMuted),
                        SizedBox(width: 4),
                        Text(
                          'WHO IMCI Protocol',
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: MalaikaColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 4),
                    Text(
                      'Please show this report to a health worker',
                      style: TextStyle(
                        fontSize: 11,
                        color: MalaikaColors.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _findingPill(String label, bool isPositive) {
    final color =
        isPositive ? MalaikaColors.yellow : MalaikaColors.green;
    return Container(
      padding:
          const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        border: Border.all(color: color.withValues(alpha: 0.2)),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isPositive
                ? Icons.circle
                : Icons.check_circle_rounded,
            size: 10,
            color: color,
          ),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: color),
          ),
        ],
      ),
    );
  }
}

// =============================================================================
// Vision Summary Card — shows aggregated camera findings
// =============================================================================

class _VisionSummaryCard extends StatelessWidget {
  final Map<String, dynamic> metadata;
  const _VisionSummaryCard({required this.metadata});

  @override
  Widget build(BuildContext context) {
    final findings =
        metadata['findings'] as Map<String, VisionFinding>;
    final notes = (metadata['notes'] as List<String>?) ?? [];

    // Show what the vision model actually found
    final detected = findings.entries.where((e) => e.value.detected).toList();
    final clear = findings.entries.where((e) => !e.value.detected).toList();

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: MalaikaColors.primaryLight,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
              color: MalaikaColors.primary.withValues(alpha: 0.15)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.visibility_rounded,
                    size: 16, color: MalaikaColors.primary),
                SizedBox(width: 8),
                Text(
                  'Vision Analysis',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: MalaikaColors.primary,
                  ),
                ),
              ],
            ),
            // Model's own observation
            if (notes.isNotEmpty) ...[
              const SizedBox(height: 10),
              Text(
                notes.first,
                style: const TextStyle(
                  fontSize: 13,
                  color: MalaikaColors.text,
                  height: 1.4,
                ),
              ),
            ],
            const SizedBox(height: 10),
            // Show detected concerns
            if (detected.isNotEmpty) ...[
              ...detected.map((e) {
                final desc = e.value.lastDescription.isNotEmpty
                    ? e.value.lastDescription
                    : e.key.replaceAll('_', ' ');
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Row(
                    children: [
                      const Icon(Icons.warning_amber_rounded,
                          size: 14, color: MalaikaColors.yellow),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(desc,
                            style: const TextStyle(
                                fontSize: 12, color: MalaikaColors.text)),
                      ),
                    ],
                  ),
                );
              }),
            ],
            // Show clear findings
            if (clear.isNotEmpty) ...[
              ...clear.map((e) {
                final desc = e.value.lastDescription.isNotEmpty
                    ? e.value.lastDescription
                    : '${e.key.replaceAll('_', ' ')} — not detected';
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Row(
                    children: [
                      const Icon(Icons.check_circle_rounded,
                          size: 14, color: MalaikaColors.green),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(desc,
                            style: const TextStyle(
                                fontSize: 12, color: MalaikaColors.text)),
                      ),
                    ],
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }
}

// =============================================================================
// Reconciliation Warning Card — Q&A vs Vision conflict
// =============================================================================

class _ReconciliationWarningCard extends StatelessWidget {
  final Map<String, dynamic> metadata;
  const _ReconciliationWarningCard({required this.metadata});

  @override
  Widget build(BuildContext context) {
    final category = metadata['category'] as String;
    final qaValue = metadata['qaValue'] as String;
    final visionValue = metadata['visionValue'] as String;
    final confidence = metadata['confidence'] as double;
    final message = metadata['message'] as String;
    final recommendation = metadata['recommendation'] as String;
    final severity = metadata['severity'] as String;

    final isHigh = severity == 'high';
    final borderColor =
        isHigh ? MalaikaColors.red : MalaikaColors.yellow;
    final bgColor = isHigh ? MalaikaColors.redLight : MalaikaColors.yellowLight;
    final iconColor = isHigh ? MalaikaColors.red : MalaikaColors.yellow;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: borderColor.withValues(alpha: 0.3)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Row(
              children: [
                Icon(Icons.compare_arrows_rounded,
                    size: 16, color: iconColor),
                const SizedBox(width: 8),
                Text(
                  'Conflict: ${_formatCategory(category)}',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: iconColor,
                  ),
                ),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: iconColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    '${(confidence * 100).round()}% confidence',
                    style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w600,
                      color: iconColor,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),

            // Q&A vs Vision comparison
            Row(
              children: [
                Expanded(
                  child: _sourceBox(
                    'Questionnaire',
                    qaValue,
                    Icons.chat_bubble_outline_rounded,
                    MalaikaColors.textSecondary,
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: Icon(Icons.sync_problem_rounded,
                      size: 20, color: iconColor),
                ),
                Expanded(
                  child: _sourceBox(
                    'Camera',
                    visionValue,
                    Icons.visibility_rounded,
                    iconColor,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),

            // Message
            Text(
              message,
              style: const TextStyle(
                fontSize: 12,
                color: MalaikaColors.text,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 8),

            // Recommendation
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.6),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.lightbulb_outline_rounded,
                      size: 14, color: iconColor),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      recommendation,
                      style: TextStyle(
                        fontSize: 11,
                        color: MalaikaColors.text,
                        fontWeight:
                            isHigh ? FontWeight.w600 : FontWeight.normal,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _sourceBox(
      String label, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 10, color: color),
              const SizedBox(width: 4),
              Text(label,
                  style: TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w600,
                      color: color)),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: TextStyle(
                fontSize: 10,
                color: color,
                fontWeight: FontWeight.w500),
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  String _formatCategory(String category) {
    return category
        .split('_')
        .map((w) =>
            w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');
  }
}
