import 'package:flutter/material.dart';
import '../theme/malaika_theme.dart';
import '../widgets/orb_button.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/imci_progress_bar.dart';
import '../widgets/classification_card.dart';
import '../widgets/skill_card.dart';
import '../widgets/finding_chip.dart';
import '../widgets/danger_alert_banner.dart';
import '../widgets/image_request_card.dart';

/// Main assessment screen — voice orb, chat, skill cards, classifications.
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
  int _currentStep = 0; // 0 = not started, 1-5 = clinical steps
  final int _totalSteps = 5;

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

  void _addClassification(String step, String severity, String label, String reasoning) {
    setState(() {
      _chatItems.add(_ChatItem(
        type: _ChatItemType.classification,
        metadata: {'step': step, 'severity': severity, 'label': label, 'reasoning': reasoning},
      ));
    });
    _scrollToBottom();
  }

  void _addSkillCard(String skillName, String description, {bool done = false}) {
    setState(() {
      _chatItems.add(_ChatItem(
        type: _ChatItemType.skillCard,
        metadata: {'skill': skillName, 'description': description, 'done': done},
      ));
    });
    _scrollToBottom();
  }

  void _addDangerAlert(String message) {
    setState(() {
      _chatItems.add(_ChatItem(type: _ChatItemType.dangerAlert, text: message));
    });
    _scrollToBottom();
  }

  void _addImageRequest(String prompt) {
    setState(() {
      _chatItems.add(_ChatItem(type: _ChatItemType.imageRequest, text: prompt));
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
        _voiceState = VoiceState.thinking;
        // Simulate processing
        Future.delayed(const Duration(seconds: 2), () {
          if (mounted) {
            setState(() => _voiceState = VoiceState.speaking);
            Future.delayed(const Duration(seconds: 2), () {
              if (mounted) setState(() => _voiceState = VoiceState.listening);
            });
          }
        });
      }
    });
  }

  void _sendText() {
    final text = _textController.text.trim();
    if (text.isEmpty) return;
    _textController.clear();
    _addUserMessage(text);

    // TODO: Process through ChatEngine + inference service
    // For now, simulate a response
    setState(() => _voiceState = VoiceState.thinking);
    Future.delayed(const Duration(seconds: 1), () {
      if (!mounted) return;
      _addBotMessage('I understand. Let me note that down.');
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
                  Text(
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

            // Progress bar (visible after step 1)
            if (_currentStep > 0)
              ImciProgressBar(
                currentStep: _currentStep,
                totalSteps: _totalSteps,
              ),

            // Orb
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: OrbButton(
                state: _voiceState,
                onTap: _onOrbTap,
              ),
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
                    case _ChatItemType.dangerAlert:
                      return DangerAlertBanner(message: item.text!);
                    case _ChatItemType.imageRequest:
                      return ImageRequestCard(
                        prompt: item.text!,
                        onTap: () {
                          // TODO: Open camera
                        },
                      );
                  }
                },
              ),
            ),

            // Input bar
            Container(
              padding: EdgeInsets.only(
                left: 10,
                right: 10,
                top: 8,
                bottom: MediaQuery.of(context).padding.bottom + 8,
              ),
              decoration: BoxDecoration(
                color: MalaikaColors.surface,
                border: Border(top: BorderSide(color: Colors.white.withOpacity(0.06))),
              ),
              child: Row(
                children: [
                  // Camera button
                  _BarButton(
                    icon: Icons.camera_alt_outlined,
                    onTap: () {
                      // TODO: Open camera
                    },
                  ),
                  const SizedBox(width: 6),

                  // Text input
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

                  // Send button
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

// Internal chat item model
enum _ChatItemType { userMessage, botMessage, classification, skillCard, dangerAlert, imageRequest }

class _ChatItem {
  final _ChatItemType type;
  final String? text;
  final Map<String, dynamic>? metadata;

  _ChatItem({required this.type, this.text, this.metadata});
}

// Small bar button widget
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
        width: 42,
        height: 42,
        decoration: BoxDecoration(
          color: color ?? Colors.white.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Icon(icon, color: color != null ? MalaikaColors.background : MalaikaColors.textMuted, size: 20),
      ),
    );
  }
}
