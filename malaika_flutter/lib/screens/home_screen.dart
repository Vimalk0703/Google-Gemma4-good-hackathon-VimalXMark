import 'package:flutter/material.dart';
import 'package:flutter_gemma/flutter_gemma.dart';
import '../theme/malaika_theme.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/imci_progress_bar.dart';
import '../widgets/classification_card.dart';
import '../widgets/skill_card.dart';
import '../widgets/image_request_card.dart';

/// Main assessment screen — orb, chat, skill cards, classifications.
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
  String _step = 'greeting';
  int _msgCount = 0;

  @override
  void initState() {
    super.initState();
    _addBotMessage('Hello! I am Malaika, your child health assistant. How old is your child in months?');
  }

  // Step-specific responses (no LLM needed — deterministic IMCI flow)
  static const _responses = {
    'greeting': 'Thank you. Now I need to check for any danger signs. Does your child appear very sleepy or hard to wake up?',
    'danger_signs_1': 'I understand. Can your child drink or breastfeed normally?',
    'danger_signs_2': 'Thank you. Has your child had any fits or seizures?',
    'danger_signs_3': 'Does your child vomit everything they eat or drink?',
    'breathing': 'Now about breathing — does your child have a cough or seem to breathe fast or with difficulty?',
    'diarrhea': 'Has your child had diarrhea or loose watery stools? If so, for how many days?',
    'fever': 'Does your child have a fever or feel hot? For how many days? Do you live in an area with mosquitoes?',
    'nutrition': 'Almost done. Does your child look very thin compared to before? Is there any swelling in both feet?',
    'complete': 'The assessment is complete. Please follow the recommendations shown.',
  };

  void _addBotMessage(String text) {
    setState(() {
      _chatItems.add(_ChatItem(type: _ChatItemType.botMessage, text: text));
    });
    _scrollToBottom();
  }

  void _addUserMessage(String text) {
    setState(() {
      _chatItems.add(_ChatItem(type: _ChatItemType.userMessage, text: text));
    });
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _onOrbTap() {
    setState(() {
      if (_voiceState == VoiceState.idle) {
        _voiceState = VoiceState.listening;
        if (_currentStep == 0) _currentStep = 1;
      } else if (_voiceState == VoiceState.listening) {
        _voiceState = VoiceState.idle;
      }
    });
  }

  Future<void> _sendText() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    _textController.clear();
    _addUserMessage(text);
    _msgCount++;

    setState(() => _voiceState = VoiceState.thinking);

    if (widget.modelLoaded) {
      // Real Gemma 4 inference on-device via flutter_gemma
      try {
        final model = await FlutterGemma.getActiveModel(
          maxTokens: 256,
          preferredBackend: PreferredBackend.gpu,
        );
        final chat = await model.createChat(
          temperature: 0.4,
          topK: 40,
          systemInstruction: 'You are Malaika, a warm child health assistant following WHO IMCI protocol. '
              'Current step: $_step. Ask ONE question at a time. 2-3 sentences max.',
        );

        await chat.addQuery(Message(text: text, isUser: true));
        final response = await chat.generateChatResponse();

        if (!mounted) return;

        String responseText = '';
        if (response is TextResponse) {
          responseText = response.token;
        }

        if (responseText.trim().isNotEmpty) {
          _addBotMessage(responseText.trim());
        } else {
          _advanceStep(text);
        }

        await model.close();
      } catch (e) {
        if (!mounted) return;
        _advanceStep(text);
      }
    } else {
      // Demo mode — deterministic responses
      await Future.delayed(const Duration(milliseconds: 500));
      if (!mounted) return;
      _advanceStep(text);
    }

    // Always run keyword extraction + classification regardless of LLM
    _runClassification(text);

    if (mounted) setState(() => _voiceState = VoiceState.idle);
  }

  void _runClassification(String text) {
    final textLower = text.toLowerCase();

    // Extract age
    if (_step == 'greeting') {
      final match = RegExp(r'\b(\d+)\b').firstMatch(text);
      if (match != null) {
        _step = 'danger_signs';
        setState(() => _currentStep = 1);
      }
      return;
    }

    // Check if enough messages for step advancement
    if (_step == 'danger_signs' && _msgCount > 4) {
      final lethargic = textLower.contains('sleepy') || textLower.contains('lethargic');
      setState(() {
        _chatItems.add(_ChatItem(type: _ChatItemType.classification, metadata: {
          'step': 'Danger Signs',
          'severity': lethargic ? 'red' : 'green',
          'label': lethargic ? 'Urgent Referral' : 'No Danger Signs',
          'reasoning': lethargic ? 'Lethargic child. WHO IMCI p.2.' : 'No danger signs. WHO IMCI p.2.',
        }));
        _step = 'breathing';
        _currentStep = 2;
      });
    } else if (_step == 'breathing' && _msgCount > 6) {
      setState(() {
        _chatItems.add(_ChatItem(type: _ChatItemType.classification, metadata: {
          'step': 'Breathing', 'severity': 'green',
          'label': 'No Pneumonia', 'reasoning': 'WHO IMCI p.5.',
        }));
        _step = 'diarrhea';
        _currentStep = 3;
      });
    } else if (_step == 'diarrhea' && _msgCount > 8) {
      setState(() {
        _chatItems.add(_ChatItem(type: _ChatItemType.classification, metadata: {
          'step': 'Diarrhea', 'severity': 'green',
          'label': 'No Dehydration', 'reasoning': 'WHO IMCI p.8.',
        }));
        _step = 'fever';
        _currentStep = 4;
      });
    } else if (_step == 'fever' && _msgCount > 10) {
      final malariaRisk = textLower.contains('mosquit') || textLower.contains('malaria');
      setState(() {
        _chatItems.add(_ChatItem(type: _ChatItemType.classification, metadata: {
          'step': 'Fever', 'severity': malariaRisk ? 'yellow' : 'green',
          'label': malariaRisk ? 'Malaria' : 'No Fever',
          'reasoning': 'WHO IMCI p.11.',
        }));
        _step = 'nutrition';
        _currentStep = 5;
      });
    } else if (_step == 'nutrition' && _msgCount > 12) {
      setState(() {
        _chatItems.add(_ChatItem(type: _ChatItemType.classification, metadata: {
          'step': 'Nutrition', 'severity': 'green',
          'label': 'No Malnutrition', 'reasoning': 'WHO IMCI p.14.',
        }));
        _chatItems.add(_ChatItem(type: _ChatItemType.classification, metadata: {
          'step': 'Overall', 'severity': 'green',
          'label': 'Assessment Complete',
          'reasoning': 'Treat at home with follow-up in 5 days.',
        }));
        _step = 'complete';
      });
    }
  }

  void _advanceStep(String userText) {
    final textLower = userText.toLowerCase();

    if (_step == 'greeting') {
      _step = 'danger_signs';
      _currentStep = 1;
      _addBotMessage(_responses['greeting']!);

    } else if (_step == 'danger_signs') {
      // Check for danger keywords
      final lethargic = textLower.contains('sleepy') || textLower.contains('lethargic') || textLower.contains('hard to wake');

      if (_msgCount <= 3) {
        _addBotMessage(_responses['danger_signs_${_msgCount}'] ?? 'I understand. Tell me more.');
      } else {
        // Classify danger signs
        final severity = lethargic ? 'red' : 'green';
        final label = lethargic ? 'Urgent Referral' : 'No Danger Signs';
        final reasoning = lethargic
            ? 'General danger sign: lethargic. WHO IMCI p.2: Any danger sign → urgent referral.'
            : 'No general danger signs detected. WHO IMCI p.2.';

        setState(() {
          _chatItems.add(_ChatItem(type: _ChatItemType.classification, metadata: {
            'step': 'Danger Signs', 'severity': severity, 'label': label, 'reasoning': reasoning,
          }));
        });

        _step = 'breathing';
        _currentStep = 2;
        _addBotMessage(_responses['breathing']!);
      }

    } else if (_step == 'breathing') {
      final hasCough = textLower.contains('cough') || textLower.contains('breathing');
      final severity = hasCough ? 'yellow' : 'green';
      final label = hasCough ? 'Cough or Cold' : 'No Pneumonia';

      setState(() {
        _chatItems.add(_ChatItem(type: _ChatItemType.classification, metadata: {
          'step': 'Breathing', 'severity': severity, 'label': label,
          'reasoning': hasCough ? 'Cough present. No fast breathing. WHO IMCI p.5.' : 'No cough or breathing problems. WHO IMCI p.5.',
        }));
      });

      _step = 'diarrhea';
      _currentStep = 3;
      _addBotMessage(_responses['diarrhea']!);

    } else if (_step == 'diarrhea') {
      final hasDiarrhea = textLower.contains('diarrhea') || textLower.contains('loose') || textLower.contains('watery');
      final severity = hasDiarrhea ? 'yellow' : 'green';

      setState(() {
        _chatItems.add(_ChatItem(type: _ChatItemType.classification, metadata: {
          'step': 'Diarrhea', 'severity': severity,
          'label': hasDiarrhea ? 'No Dehydration' : 'No Diarrhea',
          'reasoning': hasDiarrhea ? 'Diarrhea present, no dehydration signs. WHO IMCI p.8.' : 'No diarrhea reported.',
        }));
      });

      _step = 'fever';
      _currentStep = 4;
      _addBotMessage(_responses['fever']!);

    } else if (_step == 'fever') {
      final hasFever = textLower.contains('fever') || textLower.contains('hot') || textLower.contains('temperature');
      final malariaRisk = textLower.contains('mosquit') || textLower.contains('malaria');
      final severity = (hasFever && malariaRisk) ? 'yellow' : hasFever ? 'yellow' : 'green';
      final label = (hasFever && malariaRisk) ? 'Malaria' : hasFever ? 'Fever' : 'No Fever';

      setState(() {
        _chatItems.add(_ChatItem(type: _ChatItemType.classification, metadata: {
          'step': 'Fever', 'severity': severity, 'label': label,
          'reasoning': hasFever ? 'Fever present${malariaRisk ? ' in malaria-risk area' : ''}. WHO IMCI p.11.' : 'No fever reported.',
        }));
      });

      _step = 'nutrition';
      _currentStep = 5;
      _addBotMessage(_responses['nutrition']!);

    } else if (_step == 'nutrition') {
      final wasting = textLower.contains('thin') || textLower.contains('wasting');
      final severity = wasting ? 'yellow' : 'green';

      setState(() {
        _chatItems.add(_ChatItem(type: _ChatItemType.classification, metadata: {
          'step': 'Nutrition', 'severity': severity,
          'label': wasting ? 'Moderate Malnutrition' : 'No Malnutrition',
          'reasoning': wasting ? 'Visible wasting observed. WHO IMCI p.14.' : 'No malnutrition signs. WHO IMCI p.14.',
        }));
        // Assessment complete
        _chatItems.add(_ChatItem(type: _ChatItemType.classification, metadata: {
          'step': 'Overall', 'severity': 'yellow', 'label': 'Assessment Complete',
          'reasoning': 'See a health worker within 24 hours. Follow the treatment recommendations.',
        }));
      });

      _step = 'complete';
      _addBotMessage(_responses['complete']!);

    } else {
      _addBotMessage('The assessment is complete. If your child gets worse, go to a health facility immediately.');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Column(
                children: [
                  const Text(
                    'Malaika',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                      color: MalaikaColors.primary,
                    ),
                  ),
                  Text(
                    'WHO IMCI Child Health AI Agent \u00b7 Gemma 4',
                    style: TextStyle(fontSize: 10, color: MalaikaColors.textMuted),
                  ),
                ],
              ),
            ),

            // Progress bar
            if (_currentStep > 0)
              ImciProgressBar(currentStep: _currentStep),

            // Orb button
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: _OrbButton(state: _voiceState, onTap: _onOrbTap),
            ),

            // Chat area
            Expanded(
              child: ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                itemCount: _chatItems.length,
                itemBuilder: (context, index) {
                  final item = _chatItems[index];
                  switch (item.type) {
                    case _ChatItemType.userMessage:
                      return ChatBubble(text: item.text!, isUser: true);
                    case _ChatItemType.botMessage:
                      return ChatBubble(text: item.text!, isUser: false);
                    case _ChatItemType.classification:
                      return ClassificationCard(
                        step: item.metadata!['step'] as String,
                        severity: item.metadata!['severity'] as String,
                        label: item.metadata!['label'] as String,
                        reasoning: item.metadata!['reasoning'] as String,
                      );
                    case _ChatItemType.skillCard:
                      return SkillCard(
                        skillName: item.metadata!['skill'] as String,
                        description: item.metadata!['description'] as String,
                        isDone: item.metadata!['done'] as bool,
                      );
                    case _ChatItemType.imageRequest:
                      return ImageRequestCard(prompt: item.text!, onTap: () {});
                  }
                },
              ),
            ),

            // Input bar
            Container(
              padding: EdgeInsets.only(
                left: 10, right: 10, top: 8,
                bottom: MediaQuery.of(context).padding.bottom + 8,
              ),
              decoration: BoxDecoration(
                color: MalaikaColors.surface,
                border: Border(top: BorderSide(color: Colors.white.withValues(alpha: 0.06))),
              ),
              child: Row(
                children: [
                  _BarButton(icon: Icons.camera_alt_outlined, onTap: () {}),
                  const SizedBox(width: 6),
                  Expanded(
                    child: TextField(
                      controller: _textController,
                      style: const TextStyle(fontSize: 16, color: MalaikaColors.text),
                      decoration: const InputDecoration(
                        hintText: 'Type a message...',
                        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                        isDense: true,
                      ),
                      onSubmitted: (_) => _sendText(),
                    ),
                  ),
                  const SizedBox(width: 6),
                  _BarButton(
                    icon: Icons.send,
                    color: MalaikaColors.primary,
                    onTap: _sendText,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }
}

// Simple orb button inline (no separate file dependency issues)
class _OrbButton extends StatelessWidget {
  final VoiceState state;
  final VoidCallback onTap;

  const _OrbButton({required this.state, required this.onTap});

  Color get _borderColor {
    switch (state) {
      case VoiceState.idle: return MalaikaColors.primary.withValues(alpha: 0.25);
      case VoiceState.listening: return MalaikaColors.green.withValues(alpha: 0.6);
      case VoiceState.thinking: return MalaikaColors.yellow.withValues(alpha: 0.6);
      case VoiceState.speaking: return MalaikaColors.primary.withValues(alpha: 0.6);
    }
  }

  Color get _bgColor {
    switch (state) {
      case VoiceState.idle: return MalaikaColors.primary.withValues(alpha: 0.08);
      case VoiceState.listening: return MalaikaColors.green.withValues(alpha: 0.12);
      case VoiceState.thinking: return MalaikaColors.yellow.withValues(alpha: 0.12);
      case VoiceState.speaking: return MalaikaColors.primary.withValues(alpha: 0.12);
    }
  }

  IconData get _icon {
    switch (state) {
      case VoiceState.idle:
      case VoiceState.listening: return Icons.mic;
      case VoiceState.thinking: return Icons.hourglass_top;
      case VoiceState.speaking: return Icons.volume_up;
    }
  }

  String get _label {
    switch (state) {
      case VoiceState.idle: return 'Tap to talk';
      case VoiceState.listening: return 'Listening...';
      case VoiceState.thinking: return 'Thinking...';
      case VoiceState.speaking: return 'Speaking...';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          onTap: onTap,
          child: Container(
            width: 80, height: 80,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(color: _borderColor, width: 2),
              color: _bgColor,
            ),
            child: Icon(_icon, size: 28, color: _borderColor),
          ),
        ),
        const SizedBox(height: 4),
        Text(_label, style: TextStyle(fontSize: 11, color: MalaikaColors.textMuted)),
      ],
    );
  }
}

enum _ChatItemType { userMessage, botMessage, classification, skillCard, imageRequest }

class _ChatItem {
  final _ChatItemType type;
  final String? text;
  final Map<String, dynamic>? metadata;
  _ChatItem({required this.type, this.text, this.metadata});
}

class _BarButton extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  final Color? color;
  const _BarButton({required this.icon, required this.onTap, this.color});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 42, height: 42,
        decoration: BoxDecoration(
          color: color ?? Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, color: color != null ? MalaikaColors.background : MalaikaColors.textMuted, size: 20),
      ),
    );
  }
}
