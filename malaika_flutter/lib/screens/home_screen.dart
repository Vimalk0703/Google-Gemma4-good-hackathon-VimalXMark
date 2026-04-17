import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/imci_progress_bar.dart';
import '../widgets/classification_card.dart';
import '../widgets/skill_card.dart';
import '../widgets/image_request_card.dart';
import '../inference/inference_service.dart';
import '../core/chat_engine.dart';

/// Main assessment screen — orb, chat, skill cards, classifications.
class HomeScreen extends StatefulWidget {
  final InferenceService? inference;

  const HomeScreen({super.key, this.inference});

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
  late final ChatEngine _engine;
  bool _hasModel = false;

  @override
  void initState() {
    super.initState();
    _engine = ChatEngine();
    _hasModel = widget.inference != null;

    // Process initial greeting
    final result = _engine.process(userText: 'Hi');
    _addBotMessage(result['text'] as String? ?? 'Hello! I am Malaika. How old is your child in months?');
    _processEvents(result['events'] as List<Map<String, dynamic>>? ?? []);
  }

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

  void _processEvents(List<Map<String, dynamic>> events) {
    for (final event in events) {
      final type = event['type'] as String?;
      if (type == 'step_change') {
        setState(() => _currentStep = (event['index'] as int?) ?? _currentStep);
      } else if (type == 'classification') {
        setState(() {
          _chatItems.add(_ChatItem(
            type: _ChatItemType.classification,
            metadata: {
              'step': event['step'] as String? ?? '',
              'severity': event['severity'] as String? ?? 'green',
              'label': event['label'] as String? ?? '',
              'reasoning': event['reasoning'] as String? ?? '',
            },
          ));
        });
      } else if (type == 'skill_invoked') {
        setState(() {
          _chatItems.add(_ChatItem(
            type: _ChatItemType.skillCard,
            metadata: {
              'skill': event['skill'] as String? ?? '',
              'description': event['description'] as String? ?? '',
              'done': false,
            },
          ));
        });
      } else if (type == 'image_request') {
        setState(() {
          _chatItems.add(_ChatItem(
            type: _ChatItemType.imageRequest,
            text: event['prompt'] as String? ?? 'Take a photo',
          ));
        });
      } else if (type == 'danger_alert') {
        _addBotMessage('WARNING: ${event['message']}');
      } else if (type == 'assessment_complete') {
        setState(() {
          _chatItems.add(_ChatItem(
            type: _ChatItemType.classification,
            metadata: {
              'step': 'Overall',
              'severity': event['severity'] as String? ?? 'green',
              'label': 'Assessment Complete',
              'reasoning': event['urgency'] as String? ?? '',
            },
          ));
        });
      }
    }
    _scrollToBottom();
  }

  Future<void> _sendText() async {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    _textController.clear();
    _addUserMessage(text);

    setState(() => _voiceState = VoiceState.thinking);

    // Process through ChatEngine (keyword extraction + IMCI protocol)
    final result = _engine.process(userText: text);
    final events = (result['events'] as List<Map<String, dynamic>>?) ?? [];

    // Generate response
    String response;
    if (_hasModel && widget.inference != null) {
      // Use Gemma 4 on-device for response generation
      try {
        final systemPrompt = result['systemPrompt'] as String? ?? '';
        final stepContext = result['stepContext'] as String? ?? '';
        final prompt = '$stepContext\n\nCaregiver says: $text';
        response = await widget.inference!.generate(prompt, systemInstruction: systemPrompt, maxTokens: 200);
        if (response.trim().isEmpty) {
          response = result['text'] as String? ?? 'I understand. Tell me more.';
        }
      } catch (e) {
        response = result['text'] as String? ?? 'I understand. Tell me more.';
      }
    } else {
      // Demo mode — use ChatEngine's built-in response
      response = result['text'] as String? ?? 'I understand. Tell me more.';
    }

    _engine.recordAssistantResponse(response);

    if (!mounted) return;

    // Show events (classifications, skill cards, etc.)
    _processEvents(events);

    // Show response
    _addBotMessage(response);
    setState(() => _voiceState = VoiceState.idle);
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
