import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/imci_progress_bar.dart';
import '../widgets/classification_card.dart';
import '../widgets/skill_card.dart';
import '../widgets/image_request_card.dart';

/// Main assessment screen — orb, chat, skill cards, classifications.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

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

  @override
  void initState() {
    super.initState();
    _addBotMessage('Tap the circle above to start your child\'s health check.');
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

  void _sendText() {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    _textController.clear();
    _addUserMessage(text);

    // Simulate a response
    setState(() => _voiceState = VoiceState.thinking);
    Future.delayed(const Duration(seconds: 1), () {
      if (!mounted) return;
      _addBotMessage('Thank you. Let me note that down.');

      // Demo: show a classification after a few messages
      if (_chatItems.where((c) => c.type == _ChatItemType.userMessage).length == 2) {
        setState(() {
          _chatItems.add(_ChatItem(
            type: _ChatItemType.classification,
            metadata: {
              'step': 'danger_signs',
              'severity': 'green',
              'label': 'No Danger Signs',
              'reasoning': 'No general danger signs detected. WHO IMCI p.2.',
            },
          ));
          _currentStep = 2;
        });
      }

      setState(() => _voiceState = VoiceState.idle);
    });
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
