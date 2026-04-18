import 'package:flutter/material.dart';
import 'package:flutter_gemma/flutter_gemma.dart';
import '../theme/malaika_theme.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/imci_progress_bar.dart';
import '../widgets/classification_card.dart';
import '../widgets/skill_card.dart';
import '../widgets/image_request_card.dart';
import '../core/imci_protocol.dart';

/// IMCI assessment driven by Dart code with Gemma 4 for natural language.
///
/// Flow per question:
///   1. Dart picks the next IMCI question
///   2. Gemma 4 rephrases it naturally (single fresh LLM call)
///   3. User answers
///   4. Dart extracts finding via keywords
///   5. When step is complete → deterministic WHO classification card
///   6. Repeat for next step

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
  int _currentStep = 0;

  // IMCI state machine
  int _stepIndex = 0; // 0=greeting, 1=danger, 2=breathing, 3=diarrhea, 4=fever, 5=nutrition, 6=complete
  int _questionIndex = 0; // Which question within the current step
  bool _waitingForAnswer = false; // True when we've asked a question and waiting for user reply

  // Clinical findings
  int _ageMonths = 0;
  bool _lethargic = false;
  bool _unableToDrink = false;
  bool _vomitsEverything = false;
  bool _convulsions = false;
  bool _hasCough = false;
  bool _hasDiarrhea = false;
  int _diarrheaDays = 0;
  bool _bloodInStool = false;
  bool _hasFever = false;
  int _feverDays = 0;
  bool _stiffNeck = false;
  bool _malariaRisk = false;
  bool _visibleWasting = false;
  bool _edema = false;

  // All IMCI questions in order
  static const _steps = [
    'greeting',
    'danger_signs',
    'breathing',
    'diarrhea',
    'fever',
    'nutrition',
    'complete',
  ];

  // Questions per step with fallback text
  static const _questions = <String, List<Map<String, String>>>{
    'greeting': [
      {'id': 'age', 'ask': 'Hello! I am Malaika, your child health assistant. How old is your child in months?'},
    ],
    'danger_signs': [
      {'id': 'alertness', 'ask': 'Is your child very sleepy or hard to wake up?'},
      {'id': 'drinking', 'ask': 'Can your child drink or breastfeed normally?'},
      {'id': 'vomiting', 'ask': 'Does your child vomit everything they eat or drink?'},
      {'id': 'convulsions', 'ask': 'Has your child had any fits or seizures during this illness?'},
    ],
    'breathing': [
      {'id': 'cough', 'ask': 'Does your child have a cough or any difficulty breathing?'},
    ],
    'diarrhea': [
      {'id': 'diarrhea', 'ask': 'Has your child had diarrhea or loose watery stools?'},
      {'id': 'diarrhea_days', 'ask': 'How many days has the diarrhea lasted?'},
      {'id': 'blood_stool', 'ask': 'Is there any blood in the stool?'},
    ],
    'fever': [
      {'id': 'fever', 'ask': 'Does your child have a fever or feel hot?'},
      {'id': 'fever_days', 'ask': 'How many days has the fever lasted?'},
      {'id': 'stiff_neck', 'ask': 'Does your child have a stiff neck?'},
      {'id': 'malaria', 'ask': 'Do you live in an area with mosquitoes or malaria?'},
    ],
    'nutrition': [
      {'id': 'wasting', 'ask': 'Does your child look very thin? Are ribs or bones visible?'},
      {'id': 'edema', 'ask': 'Is there any swelling in both of your child\'s feet?'},
    ],
  };

  String get _currentStepName => _steps[_stepIndex.clamp(0, _steps.length - 1)];

  @override
  void initState() {
    super.initState();
    // Ask first question (greeting/age)
    _askCurrentQuestion();
  }

  /// Generate the question using LLM or fallback
  Future<void> _askCurrentQuestion() async {
    final stepName = _currentStepName;
    final questions = _questions[stepName];

    if (stepName == 'complete' || questions == null) return;
    if (_questionIndex >= questions.length) return;

    final q = questions[_questionIndex];
    final fallbackText = q['ask']!;
    final qId = q['id']!;

    // Try LLM to make it natural, otherwise use fallback
    if (widget.modelLoaded) {
      setState(() => _voiceState = VoiceState.thinking);
      final response = await _singleLLMCall(
        'Rephrase this question warmly in 1 sentence. '
        'Do NOT introduce yourself. Do NOT say your name. '
        'Do NOT assume symptoms. Just ask: "$fallbackText"'
      );
      if (mounted) {
        final cleanResponse = response.replaceAll(RegExp(r'^\s*[,.:;]\s*$'), '').trim();
        final displayText = cleanResponse.isNotEmpty ? cleanResponse : fallbackText;
        _addBotMessage(displayText);
        debugPrint('[MALAIKA] Step=$stepName Q=$qId Asked via ${cleanResponse.isNotEmpty ? "LLM" : "FALLBACK"}: "$displayText"');
      }
    } else {
      _addBotMessage(fallbackText);
      debugPrint('[MALAIKA] Step=$stepName Q=$qId Asked via FALLBACK: "$fallbackText"');
    }

    _waitingForAnswer = true;
    if (mounted) setState(() => _voiceState = VoiceState.idle);
  }

  /// Single LLM call with fresh context (avoids context overflow)
  Future<String> _singleLLMCall(String prompt) async {
    try {
      final model = await FlutterGemma.getActiveModel(maxTokens: 200);
      final chat = await model.createChat(temperature: 0.4, topK: 40,
          systemInstruction: 'You are a caring health assistant. Rephrase questions warmly in 1 sentence. Never introduce yourself.');
      await chat.addQuery(Message(text: prompt, isUser: true));
      final response = await chat.generateChatResponse();
      return response is TextResponse ? response.token.trim() : '';
    } catch (e) {
      debugPrint('[MALAIKA] LLM error: $e');
      return '';
    }
  }

  Future<void> _sendText() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    _textController.clear();
    _addUserMessage(text);
    debugPrint('[MALAIKA] User said: "$text" | Step=$_currentStepName Q=$_questionIndex');

    if (!_waitingForAnswer) return;
    _waitingForAnswer = false;

    setState(() => _voiceState = VoiceState.thinking);

    // 1. Extract finding from user's answer
    _extractFinding(text);

    // 2. Move to next question or classify step
    _questionIndex++;

    // Handle conditional questions (skip if parent answer is no)
    _skipConditionalQuestions();

    final questions = _questions[_currentStepName];
    if (questions != null && _questionIndex >= questions.length) {
      // Step complete → classify and advance
      await _classifyAndAdvance();
    } else {
      // Ask next question in same step
      await _askCurrentQuestion();
    }

    if (mounted) setState(() => _voiceState = VoiceState.idle);
  }

  void _skipConditionalQuestions() {
    final stepName = _currentStepName;
    final questions = _questions[stepName];
    if (questions == null) return;

    // Skip diarrhea sub-questions if no diarrhea
    if (stepName == 'diarrhea' && !_hasDiarrhea && _questionIndex >= 1) {
      _questionIndex = questions.length;
    }
    // Skip fever sub-questions if no fever
    if (stepName == 'fever' && !_hasFever && _questionIndex >= 1) {
      _questionIndex = questions.length;
    }
  }

  void _extractFinding(String text) {
    final t = text.toLowerCase();
    final isYes = t == 'yes' || t.contains('yes') || t == 'yeah' || t == 'ya';
    final stepName = _currentStepName;
    final questions = _questions[stepName];
    if (questions == null || _questionIndex >= questions.length) return;
    final qId = questions[_questionIndex]['id']!;

    debugPrint('[MALAIKA] Extracting: qId=$qId text="$t" isYes=$isYes');

    switch (qId) {
      case 'age':
        final m = RegExp(r'(\d+)').firstMatch(text);
        if (m != null) _ageMonths = int.tryParse(m.group(1)!) ?? 0;
        const words = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,
          'eleven':11,'twelve':12,'eighteen':18,'twenty-four':24};
        for (final e in words.entries) {
          if (t.contains(e.key)) { _ageMonths = e.value; break; }
        }
        debugPrint('[MALAIKA] Age extracted: $_ageMonths months');
      case 'alertness':
        _lethargic = isYes || t.contains('sleepy') || t.contains('lethargic') || t.contains('drowsy') || t.contains('hard to wake');
        debugPrint('[MALAIKA] Lethargic: $_lethargic');
      case 'drinking':
        // Question: "Can your child drink?" — positive answers mean CAN drink
        final canDrink = isYes || t.contains('normal') || t.contains('fine') || t.contains('well') || t.contains('drink') || t.contains('breast');
        final cantDrink = t.contains('cannot') || t.contains("can't") || t.contains('unable') || t.contains('refuse');
        _unableToDrink = cantDrink && !canDrink;
        debugPrint('[MALAIKA] Unable to drink: $_unableToDrink (canDrink=$canDrink cantDrink=$cantDrink)');
      case 'vomiting':
        _vomitsEverything = isYes || t.contains('vomit') || t.contains('throw up');
        debugPrint('[MALAIKA] Vomits everything: $_vomitsEverything');
      case 'convulsions':
        _convulsions = isYes || t.contains('seizure') || t.contains('fit') || t.contains('convulsion') || t.contains('shaking');
        debugPrint('[MALAIKA] Convulsions: $_convulsions');
      case 'cough':
        _hasCough = isYes || t.contains('cough') || t.contains('cold') || t.contains('breathing') || t.contains('wheez') || t.contains('noise');
        debugPrint('[MALAIKA] Has cough: $_hasCough');
      case 'diarrhea':
        _hasDiarrhea = isYes || t.contains('diarrhea') || t.contains('loose') || t.contains('watery');
        debugPrint('[MALAIKA] Has diarrhea: $_hasDiarrhea');
      case 'diarrhea_days':
        final m = RegExp(r'(\d+)').firstMatch(text);
        _diarrheaDays = m != null ? (int.tryParse(m.group(1)!) ?? 0) : 0;
        debugPrint('[MALAIKA] Diarrhea days: $_diarrheaDays');
      case 'blood_stool':
        _bloodInStool = isYes || t.contains('blood');
        debugPrint('[MALAIKA] Blood in stool: $_bloodInStool');
      case 'fever':
        _hasFever = isYes || t.contains('fever') || t.contains('hot') || t.contains('temperature');
        debugPrint('[MALAIKA] Has fever: $_hasFever');
      case 'fever_days':
        final m = RegExp(r'(\d+)').firstMatch(text);
        _feverDays = m != null ? (int.tryParse(m.group(1)!) ?? 0) : 0;
        debugPrint('[MALAIKA] Fever days: $_feverDays');
      case 'stiff_neck':
        _stiffNeck = isYes || t.contains('stiff');
        debugPrint('[MALAIKA] Stiff neck: $_stiffNeck');
      case 'malaria':
        _malariaRisk = isYes || t.contains('mosquit') || t.contains('malaria');
        debugPrint('[MALAIKA] Malaria risk: $_malariaRisk');
      case 'wasting':
        _visibleWasting = isYes || t.contains('thin') || t.contains('ribs') || t.contains('bones');
        debugPrint('[MALAIKA] Visible wasting: $_visibleWasting');
      case 'edema':
        _edema = isYes || t.contains('swell') || t.contains('edema');
        debugPrint('[MALAIKA] Edema: $_edema');
    }
  }

  Future<void> _classifyAndAdvance() async {
    final stepName = _currentStepName;
    debugPrint('[MALAIKA] === CLASSIFYING STEP: $stepName ===');

    switch (stepName) {
      case 'greeting':
        // No message — just advance to first step
        break;
      case 'danger_signs':
        final result = classifyDangerSigns(lethargic: _lethargic, unableToDrink: _unableToDrink,
            vomitsEverything: _vomitsEverything, convulsions: _convulsions);
        _addClassification('Danger Signs',
            result?.severity.value ?? 'green',
            _formatLabel(result?.classification.value ?? 'no_danger_signs'),
            result?.reasoning ?? 'No general danger signs detected. WHO IMCI p.2.');
        debugPrint('[MALAIKA] Danger Signs: ${result?.severity.value ?? "green"} - ${result?.classification.value ?? "none"}');
      case 'breathing':
        final age = _ageMonths > 0 ? _ageMonths.clamp(2, 59) : 12;
        final result = classifyBreathing(ageMonths: age, hasCough: _hasCough);
        // Make the label human-readable
        final breathLabel = _hasCough ? 'Cough or Cold (No Pneumonia)' : 'Normal Breathing';
        final breathReason = _hasCough
            ? 'Cough present but no fast breathing or chest indrawing detected. WHO IMCI p.5.'
            : 'No cough or breathing problems reported. WHO IMCI p.5.';
        _addClassification('Breathing', result.severity.value, breathLabel, breathReason);
        debugPrint('[MALAIKA] Breathing: ${result.severity.value} - hasCough=$_hasCough');
      case 'diarrhea':
        if (_hasDiarrhea) {
          final result = classifyDiarrhea(hasDiarrhea: true, durationDays: _diarrheaDays,
              bloodInStool: _bloodInStool, lethargic: _lethargic);
          if (result != null) {
            _addClassification('Diarrhea', result.severity.value, _formatLabel(result.classification.value), result.reasoning);
          }
        } else {
          _addClassification('Diarrhea', 'green', 'No Diarrhea', 'No diarrhea reported.');
        }
      case 'fever':
        if (_hasFever) {
          final result = classifyFever(hasFever: true, durationDays: _feverDays,
              stiffNeck: _stiffNeck, malariaRisk: _malariaRisk);
          if (result != null) {
            _addClassification('Fever', result.severity.value, _formatLabel(result.classification.value), result.reasoning);
          }
        } else {
          _addClassification('Fever', 'green', 'No Fever', 'No fever reported.');
        }
      case 'nutrition':
        final result = classifyNutrition(visibleWasting: _visibleWasting, edema: _edema);
        _addClassification('Nutrition', result.severity.value, _formatLabel(result.classification.value), result.reasoning);
        // Show final assessment
        _showFinalAssessment();
        return; // Don't advance further
    }

    // Move to next step
    _stepIndex++;
    _questionIndex = 0;
    _currentStep = _stepIndex.clamp(0, 5);
    setState(() {});

    if (_currentStepName != 'complete') {
      await _askCurrentQuestion();
    }
  }

  void _showFinalAssessment() {
    debugPrint('[MALAIKA] === FINAL ASSESSMENT ===');
    final severities = _chatItems
        .where((c) => c.type == _ChatItemType.classification && c.metadata?['step'] != 'Assessment Complete')
        .map((c) => c.metadata?['severity'] as String? ?? 'green')
        .toList();
    final overall = severities.contains('red') ? 'red' : severities.contains('yellow') ? 'yellow' : 'green';
    final urgency = overall == 'red'
        ? 'URGENT: Take your child to the nearest health facility IMMEDIATELY.'
        : overall == 'yellow'
            ? 'See a health worker within 24 hours. Keep giving fluids.'
            : 'Treat at home. Continue feeding, give fluids. Return in 5 days if not better.';

    debugPrint('[MALAIKA] Overall: $overall');
    _addClassification('Assessment Complete', overall, 'Overall: ${overall.toUpperCase()}', urgency);

    _stepIndex = 6; // complete
    _currentStep = 5;
    setState(() {});

    // Generate final summary via LLM
    final findings = <String>[];
    if (_lethargic) findings.add('LETHARGIC (danger sign)');
    if (_unableToDrink) findings.add('Unable to drink');
    if (_vomitsEverything) findings.add('Vomits everything');
    if (_convulsions) findings.add('Convulsions');
    if (_hasCough) findings.add('Cough/breathing difficulty');
    if (_hasDiarrhea) findings.add('Diarrhea ${_diarrheaDays}d');
    if (_bloodInStool) findings.add('Blood in stool');
    if (_hasFever) findings.add('Fever ${_feverDays}d');
    if (_stiffNeck) findings.add('Stiff neck');
    if (_malariaRisk) findings.add('Malaria risk');
    if (_visibleWasting) findings.add('Visible wasting');
    if (_edema) findings.add('Edema');

    // Always show the practical summary (don't rely on LLM for this critical info)
    final summaryParts = <String>[urgency];
    if (_hasDiarrhea) summaryParts.add('Give ORS (oral rehydration salts) mixed with clean water. Give small sips often.');
    if (_hasFever) summaryParts.add('Give paracetamol for fever if available. Keep child lightly dressed.');
    if (_hasCough) summaryParts.add('Keep child warm. Watch for fast or difficult breathing.');
    summaryParts.add('Continue breastfeeding or giving fluids.');
    summaryParts.add('Return IMMEDIATELY if: child stops drinking, has seizures, or gets worse.');
    summaryParts.add('\nPlease show this assessment to a health worker.');

    _addBotMessage(summaryParts.join('\n\n'));
    debugPrint('[MALAIKA] Final summary shown with ${findings.length} findings');
  }

  String _formatLabel(String value) => value.replaceAll('_', ' ').split(' ').map((w) =>
      w.isNotEmpty ? '${w[0].toUpperCase()}${w.substring(1)}' : w).join(' ');

  void _addBotMessage(String text) {
    setState(() => _chatItems.add(_ChatItem(type: _ChatItemType.botMessage, text: text)));
    _scrollToBottom();
  }

  void _addUserMessage(String text) {
    setState(() => _chatItems.add(_ChatItem(type: _ChatItemType.userMessage, text: text)));
    _scrollToBottom();
  }

  void _addClassification(String step, String severity, String label, String reasoning) {
    setState(() => _chatItems.add(_ChatItem(type: _ChatItemType.classification,
        metadata: {'step': step, 'severity': severity, 'label': label, 'reasoning': reasoning})));
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(_scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
      }
    });
  }

  void _onOrbTap() => setState(() {
    _voiceState = _voiceState == VoiceState.idle ? VoiceState.listening : VoiceState.idle;
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: Column(children: [
              const Text('Malaika', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: MalaikaColors.primary)),
              Text('WHO IMCI Child Health AI \u00b7 Gemma 4 On-Device', style: TextStyle(fontSize: 10, color: MalaikaColors.textMuted)),
            ])),
            if (_currentStep > 0) ImciProgressBar(currentStep: _currentStep),
            Padding(padding: const EdgeInsets.symmetric(vertical: 8), child: _OrbButton(state: _voiceState, onTap: _onOrbTap)),
            Expanded(
              child: ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                itemCount: _chatItems.length,
                itemBuilder: (context, index) {
                  final item = _chatItems[index];
                  return switch (item.type) {
                    _ChatItemType.userMessage => ChatBubble(text: item.text!, isUser: true),
                    _ChatItemType.botMessage => ChatBubble(text: item.text!, isUser: false),
                    _ChatItemType.classification => ClassificationCard(
                        step: item.metadata!['step'] as String, severity: item.metadata!['severity'] as String,
                        label: item.metadata!['label'] as String, reasoning: item.metadata!['reasoning'] as String),
                    _ChatItemType.skillCard => SkillCard(skillName: item.metadata!['skill'] as String,
                        description: item.metadata!['description'] as String, isDone: item.metadata!['done'] as bool),
                    _ChatItemType.imageRequest => ImageRequestCard(prompt: item.text!, onTap: () {}),
                  };
                },
              ),
            ),
            Container(
              padding: EdgeInsets.only(left: 10, right: 10, top: 8, bottom: MediaQuery.of(context).padding.bottom + 8),
              decoration: BoxDecoration(color: MalaikaColors.surface, border: Border(top: BorderSide(color: Colors.white.withValues(alpha: 0.06)))),
              child: Row(children: [
                _BarButton(icon: Icons.camera_alt_outlined, onTap: () {}),
                const SizedBox(width: 6),
                Expanded(child: TextField(controller: _textController,
                    style: const TextStyle(fontSize: 16, color: MalaikaColors.text),
                    decoration: const InputDecoration(hintText: 'Type a message...', contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10), isDense: true),
                    onSubmitted: (_) => _sendText())),
                const SizedBox(width: 6),
                _BarButton(icon: Icons.send, color: MalaikaColors.primary, onTap: _sendText),
              ]),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() { _textController.dispose(); _scrollController.dispose(); super.dispose(); }
}

class _OrbButton extends StatelessWidget {
  final VoiceState state; final VoidCallback onTap;
  const _OrbButton({required this.state, required this.onTap});
  Color get _bc => switch (state) { VoiceState.idle => MalaikaColors.primary.withValues(alpha: 0.25), VoiceState.listening => MalaikaColors.green.withValues(alpha: 0.6), VoiceState.thinking => MalaikaColors.yellow.withValues(alpha: 0.6), VoiceState.speaking => MalaikaColors.primary.withValues(alpha: 0.6) };
  Color get _bg => switch (state) { VoiceState.idle => MalaikaColors.primary.withValues(alpha: 0.08), VoiceState.listening => MalaikaColors.green.withValues(alpha: 0.12), VoiceState.thinking => MalaikaColors.yellow.withValues(alpha: 0.12), VoiceState.speaking => MalaikaColors.primary.withValues(alpha: 0.12) };
  IconData get _ic => switch (state) { VoiceState.idle || VoiceState.listening => Icons.mic, VoiceState.thinking => Icons.hourglass_top, VoiceState.speaking => Icons.volume_up };
  String get _lb => switch (state) { VoiceState.idle => 'Tap to talk', VoiceState.listening => 'Listening...', VoiceState.thinking => 'Thinking...', VoiceState.speaking => 'Speaking...' };
  @override Widget build(BuildContext context) => Column(mainAxisSize: MainAxisSize.min, children: [
    GestureDetector(onTap: onTap, child: Container(width: 80, height: 80, decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: _bc, width: 2), color: _bg), child: Icon(_ic, size: 28, color: _bc))),
    const SizedBox(height: 4), Text(_lb, style: TextStyle(fontSize: 11, color: MalaikaColors.textMuted)),
  ]);
}

enum _ChatItemType { userMessage, botMessage, classification, skillCard, imageRequest }
class _ChatItem { final _ChatItemType type; final String? text; final Map<String, dynamic>? metadata; _ChatItem({required this.type, this.text, this.metadata}); }
class _BarButton extends StatelessWidget {
  final IconData icon; final VoidCallback onTap; final Color? color;
  const _BarButton({required this.icon, required this.onTap, this.color});
  @override Widget build(BuildContext context) => GestureDetector(onTap: onTap, child: Container(width: 42, height: 42, decoration: BoxDecoration(color: color ?? Colors.white.withValues(alpha: 0.06), borderRadius: BorderRadius.circular(12)), child: Icon(icon, color: color != null ? MalaikaColors.background : MalaikaColors.textMuted, size: 20)));
}
