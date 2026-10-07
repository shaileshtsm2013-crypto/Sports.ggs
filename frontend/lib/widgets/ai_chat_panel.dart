import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../services/analysis_provider.dart';

/// Collapsible AI Rules Chatbot side panel with Gemini / offline badge,
/// sport context pill, copy-on-long-press, and animated typing indicator.
class AIChatPanel extends StatefulWidget {
  const AIChatPanel({Key? key}) : super(key: key);

  @override
  State<AIChatPanel> createState() => _AIChatPanelState();
}

class _AIChatPanelState extends State<AIChatPanel>
    with SingleTickerProviderStateMixin {
  final TextEditingController _controller = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  // Typing dots animation
  late final AnimationController _dotController;
  late final Animation<double> _dotAnim;

  @override
  void initState() {
    super.initState();
    _dotController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat();
    _dotAnim = Tween<double>(begin: 0, end: 1).animate(_dotController);
  }

  @override
  void dispose() {
    _dotController.dispose();
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _sendMessage() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    final provider = Provider.of<AnalysisProvider>(context, listen: false);
    provider.sendChatMessage(text);
    _controller.clear();
    _scrollToBottom();
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 120), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _copyMessage(String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Copied to clipboard'),
        duration: Duration(seconds: 1),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Widget _buildProviderBadge(String provider) {
    final isGemini = provider == 'gemini';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: isGemini
            ? const Color(0xFF4ADE80).withOpacity(0.15)
            : const Color(0xFF94A3B8).withOpacity(0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(
          color: isGemini
              ? const Color(0xFF4ADE80).withOpacity(0.4)
              : const Color(0xFF475569),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isGemini ? Icons.auto_awesome : Icons.wifi_off,
            size: 9,
            color: isGemini ? const Color(0xFF4ADE80) : const Color(0xFF94A3B8),
          ),
          const SizedBox(width: 3),
          Text(
            isGemini ? 'Gemini' : 'Offline',
            style: TextStyle(
              fontSize: 9,
              color:
                  isGemini ? const Color(0xFF4ADE80) : const Color(0xFF94A3B8),
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTypingIndicator() {
    return AnimatedBuilder(
      animation: _dotAnim,
      builder: (context, _) {
        final phase = _dotAnim.value;
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(3, (i) {
            final opacity = (((phase + i / 3) % 1.0) < 0.5) ? 1.0 : 0.3;
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 2),
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: const Color(0xFF06B6D4).withOpacity(opacity),
                shape: BoxShape.circle,
              ),
            );
          }),
        );
      },
    );
  }

  Widget _buildMessageBubble(Map<String, String> msg) {
    final isUser = msg['role'] == 'user';
    final content = msg['content'] ?? '';

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: GestureDetector(
        onLongPress: () => _copyMessage(content),
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.all(10),
          constraints: const BoxConstraints(maxWidth: 268),
          decoration: BoxDecoration(
            color: isUser
                ? const Color(0xFF0284C7)
                : const Color(0xFF334155),
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(10),
              topRight: const Radius.circular(10),
              bottomLeft: Radius.circular(isUser ? 10 : 2),
              bottomRight: Radius.circular(isUser ? 2 : 10),
            ),
          ),
          child: Text(
            content,
            style: const TextStyle(fontSize: 12, height: 1.45, color: Colors.white),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<AnalysisProvider>(context);

    // Auto-scroll when new message arrives
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });

    final sportLabel = {
          'volleyball': '🏐 Volleyball',
          'kabaddi': '🤼 Kabaddi',
          'kho_kho': '🏃 Kho Kho',
        }[provider.selectedSport] ??
        provider.selectedSport.toUpperCase();

    return Container(
      width: 340,
      decoration: const BoxDecoration(
        color: Color(0xFF1E293B),
        border: Border(left: BorderSide(color: Color(0xFF334155), width: 1)),
      ),
      child: Column(
        children: [
          // ── Header ──────────────────────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            color: const Color(0xFF0F172A),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.psychology,
                        color: Color(0xFF06B6D4), size: 18),
                    const SizedBox(width: 6),
                    const Text(
                      'Rules & AI Assistant',
                      style: TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 13),
                    ),
                    const Spacer(),
                    _buildProviderBadge(provider.aiProvider),
                  ],
                ),
                const SizedBox(height: 6),
                // Sport context pill
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0284C7).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                        color: const Color(0xFF0284C7).withOpacity(0.4)),
                  ),
                  child: Text(
                    sportLabel,
                    style: const TextStyle(
                        fontSize: 11,
                        color: Color(0xFF38BDF8),
                        fontWeight: FontWeight.w500),
                  ),
                ),
              ],
            ),
          ),

          // ── Message list ─────────────────────────────────────────
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(12),
              itemCount: provider.chatMessages.length +
                  (provider.isChatLoading ? 1 : 0),
              itemBuilder: (context, index) {
                if (index == provider.chatMessages.length) {
                  // Typing indicator bubble
                  return Align(
                    alignment: Alignment.centerLeft,
                    child: Container(
                      margin: const EdgeInsets.symmetric(vertical: 4),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 14, vertical: 10),
                      decoration: BoxDecoration(
                        color: const Color(0xFF334155),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: _buildTypingIndicator(),
                    ),
                  );
                }
                return _buildMessageBubble(provider.chatMessages[index]);
              },
            ),
          ),

          // ── Input bar ────────────────────────────────────────────
          Container(
            padding: const EdgeInsets.all(8),
            color: const Color(0xFF0F172A),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    style: const TextStyle(fontSize: 13),
                    decoration: InputDecoration(
                      hintText: 'Ask about ${provider.selectedSport} rules...',
                      hintStyle: const TextStyle(
                          color: Color(0xFF64748B), fontSize: 12),
                      isDense: true,
                      filled: true,
                      fillColor: const Color(0xFF1E293B),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 8),
                    ),
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 6),
                IconButton(
                  icon: const Icon(Icons.send,
                      color: Color(0xFF06B6D4), size: 18),
                  onPressed: provider.isChatLoading ? null : _sendMessage,
                  visualDensity: VisualDensity.compact,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
