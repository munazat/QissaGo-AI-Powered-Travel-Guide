import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../core/format.dart';
import '../core/models.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/media.dart';
import 'generating_screen.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key, this.embedded = false});

  /// Inside the Plan tab, which has its own app bar.
  final bool embedded;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();
  final List<ChatMessage> _messages = [];
  ChatTurn? _turn;
  bool _waiting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _start();
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _start() async {
    setState(() {
      _error = null;
      _waiting = true;
    });
    try {
      final turn = await context.read<AppState>().api.startChat();
      if (!mounted) return;
      setState(() {
        _turn = turn;
        _messages.add(ChatMessage(fromUser: false, text: turn.reply));
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _waiting = false);
    }
  }

  void _toBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(_scroll.position.maxScrollExtent + 80,
            duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      }
    });
  }

  Future<void> _send({String? text, Map<String, dynamic>? patch, String? shown}) async {
    final turn = _turn;
    if (turn == null || _waiting) return;
    final display = shown ?? text ?? '';
    if (text == 'Create plans' && turn.ready) {
      _generate();
      return;
    }
    setState(() {
      if (display.isNotEmpty) _messages.add(ChatMessage(fromUser: true, text: display));
      _waiting = true;
    });
    _input.clear();
    _toBottom();
    try {
      final next = await context.read<AppState>().api.sendChat(turn.sessionId, text: text, patch: patch);
      if (!mounted) return;
      setState(() {
        _turn = next;
        _messages.add(ChatMessage(fromUser: false, text: next.reply));
      });
      if (next.action == 'generate') _generate();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _waiting = false);
      _toBottom();
    }
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: now.add(const Duration(days: 1)),
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: now.add(const Duration(days: 365)),
    );
    if (picked != null) {
      _send(patch: {'start_date': isoDate(picked)}, shown: longDate(picked));
    }
  }

  void _generate() {
    final turn = _turn;
    if (turn == null) return;
    Navigator.of(context)
        .push(MaterialPageRoute(builder: (_) => GeneratingScreen(sessionId: turn.sessionId, source: 'chat')));
  }

  @override
  Widget build(BuildContext context) {
    final turn = _turn;
    return Scaffold(
      appBar: widget.embedded ? null : AppBar(title: Text('Plan by chat', style: display(24))),
      body: _error != null
          ? ErrorRetry(message: _error!, onRetry: _start)
          : Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 760),
                child: Column(
                  children: [
                    if (turn != null) _PrefsBar(prefs: turn.preferences),
                    Expanded(
                      child: ListView.builder(
                        controller: _scroll,
                        padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                        itemCount: _messages.length + (_waiting ? 1 : 0),
                        itemBuilder: (_, i) => i == _messages.length ? const _Typing() : _Bubble(message: _messages[i]),
                      ),
                    ),
                    if (turn != null && !_waiting && (turn.suggestions.isNotEmpty || turn.awaiting == 'start_date'))
                      SizedBox(
                        height: 52,
                        child: ListView(
                          scrollDirection: Axis.horizontal,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                          children: [
                            if (turn.awaiting == 'start_date')
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 4),
                                child: SuggestionPill(
                                  label: 'Pick a date',
                                  icon: Icons.calendar_month_outlined,
                                  primary: true,
                                  onTap: _pickDate,
                                ),
                              ),
                            for (final s in turn.suggestions)
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 4),
                                child: SuggestionPill(
                                  label: s,
                                  primary: s == 'Create plans',
                                  onTap: () => _send(text: s),
                                ),
                              ),
                          ],
                        ),
                      ),
                    if (turn != null && turn.ready && !_waiting)
                      Padding(
                        padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                        child: SizedBox(
                          width: double.infinity,
                          child: FilledButton.icon(
                            onPressed: _generate,
                            icon: const Icon(Icons.auto_awesome),
                            label: const Text('Create plans'),
                          ),
                        ),
                      ),
                    _InputBar(
                      controller: _input,
                      enabled: turn != null && !_waiting,
                      showDate: turn != null,
                      onDate: _pickDate,
                      onSend: () {
                        final text = _input.text.trim();
                        if (text.isNotEmpty) _send(text: text);
                      },
                    ),
                  ],
                ),
              ),
            ),
    );
  }
}

class _PrefsBar extends StatelessWidget {
  const _PrefsBar({required this.prefs});

  final Map<String, dynamic> prefs;

  @override
  Widget build(BuildContext context) {
    final meta = context.watch<AppState>().meta;
    final pills = <Widget>[];
    final city = prefs['city'] as String?;
    if (city != null) pills.add(Pill(meta?.city(city)?.name ?? titleCase(city), icon: Icons.place_outlined));
    final days = prefs['days'];
    if (days != null) pills.add(Pill('$days ${days == 1 ? 'day' : 'days'}', icon: Icons.calendar_today_outlined));
    final start = DateTime.tryParse('${prefs['start_date'] ?? ''}');
    if (start != null) pills.add(Pill(shortDate(start), icon: Icons.event_outlined));
    final size = prefs['group_size'];
    final type = prefs['group_type'];
    if (size != null || type != null) {
      pills.add(Pill(size != null ? '$size' : titleCase('$type'), icon: Icons.group_outlined));
    }
    final home = prefs['home_city'] as String?;
    if (home != null) {
      pills.add(Pill('From ${meta?.city(home)?.name ?? titleCase(home)}', icon: Icons.trip_origin));
    }
    if (prefs['traveller_type'] == 'foreign') pills.add(const Pill('Foreign', icon: Icons.public));
    final budget = prefs['budget'];
    if (budget is num) pills.add(Pill(rupees(budget.toInt()), icon: Icons.payments_outlined));
    if (pills.isEmpty) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 10),
      child: Wrap(spacing: 6, runSpacing: 6, children: pills),
    );
  }
}

/// Round "Q" mark that stands for the planner in the chat.
class BotAvatar extends StatelessWidget {
  const BotAvatar({super.key, this.size = 34});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: const BoxDecoration(color: Palette.slate, shape: BoxShape.circle),
      child: Text('Q', style: display(size * 0.55, color: Colors.white)),
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final mine = message.fromUser;
    final bubble = Container(
      constraints: const BoxConstraints(maxWidth: 520),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: mine ? Palette.primary : Palette.paper,
        borderRadius: BorderRadius.only(
          topLeft: const Radius.circular(22),
          topRight: const Radius.circular(22),
          bottomLeft: Radius.circular(mine ? 22 : 6),
          bottomRight: Radius.circular(mine ? 6 : 22),
        ),
        boxShadow: [BoxShadow(color: Palette.slate.withValues(alpha: 0.06), blurRadius: 8, offset: const Offset(0, 2))],
      ),
      child: Text(
        message.text,
        style: TextStyle(
          color: mine ? Palette.onPrimary : Palette.slate,
          height: 1.45,
          fontSize: 15,
          fontWeight: mine ? FontWeight.w600 : FontWeight.w500,
        ),
      ),
    );
    return Appear(
      offset: 12,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(
          mainAxisAlignment: mine ? MainAxisAlignment.end : MainAxisAlignment.start,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            if (!mine) ...[const BotAvatar(), const SizedBox(width: 8)],
            Flexible(child: bubble),
          ],
        ),
      ),
    );
  }
}

/// Three dots that bounce one after another while the planner replies.
class TypingDots extends StatefulWidget {
  const TypingDots({super.key});

  @override
  State<TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<TypingDots> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1100))
    ..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  /// 0..1..0 bump for dot [i], staggered.
  double _lift(int i) {
    final t = (_c.value - i * 0.18) % 1.0;
    if (t >= 0.4) return 0;
    return t < 0.2 ? t / 0.2 : (0.4 - t) / 0.2;
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (_, __) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (var i = 0; i < 3; i++)
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 3),
              transform: Matrix4.translationValues(0, -6 * _lift(i), 0),
              width: 8,
              height: 8,
              decoration: BoxDecoration(
                color: Color.lerp(Palette.line, Palette.slate, _lift(i)),
                shape: BoxShape.circle,
              ),
            ),
        ],
      ),
    );
  }
}

class _Typing extends StatelessWidget {
  const _Typing();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          const BotAvatar(),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            decoration: const BoxDecoration(
              color: Palette.paper,
              borderRadius: BorderRadius.only(
                topLeft: Radius.circular(22),
                topRight: Radius.circular(22),
                bottomRight: Radius.circular(22),
                bottomLeft: Radius.circular(6),
              ),
            ),
            child: const TypingDots(),
          ),
        ],
      ),
    );
  }
}

/// Rounded suggestion button under the conversation.
class SuggestionPill extends StatelessWidget {
  const SuggestionPill({super.key, required this.label, required this.onTap, this.icon, this.primary = false});

  final String label;
  final VoidCallback onTap;
  final IconData? icon;
  final bool primary;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: primary ? Palette.primary : Palette.paper,
      shape: StadiumBorder(side: BorderSide(color: primary ? Palette.primary : Palette.line)),
      child: InkWell(
        customBorder: const StadiumBorder(),
        onTap: onTap,
        child: Container(
          constraints: const BoxConstraints(minHeight: 44),
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[Icon(icon, size: 18, color: Palette.onPrimary), const SizedBox(width: 6)],
              Text(label, style: const TextStyle(fontWeight: FontWeight.w700, color: Palette.onPrimary)),
            ],
          ),
        ),
      ),
    );
  }
}

class _InputBar extends StatelessWidget {
  const _InputBar({
    required this.controller,
    required this.enabled,
    required this.showDate,
    required this.onDate,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool enabled;
  final bool showDate;
  final VoidCallback onDate;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
        child: Row(
          children: [
            if (showDate) ...[
              IconButton(
                tooltip: 'Date',
                onPressed: enabled ? onDate : null,
                style: IconButton.styleFrom(backgroundColor: Palette.sage, minimumSize: const Size(52, 52)),
                icon: const Icon(Icons.calendar_month_outlined, color: Palette.slate),
              ),
              const SizedBox(width: 8),
            ],
            Expanded(
              child: TextField(
                controller: controller,
                enabled: enabled,
                minLines: 1,
                maxLines: 4,
                textInputAction: TextInputAction.send,
                onSubmitted: (_) => onSend(),
                decoration: fieldStyle('Message'),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filled(
              onPressed: enabled ? onSend : null,
              tooltip: 'Send',
              style: IconButton.styleFrom(
                backgroundColor: Palette.primary,
                disabledBackgroundColor: Palette.sage,
                minimumSize: const Size(52, 52),
              ),
              icon: const Icon(Icons.arrow_upward, color: Palette.onPrimary),
            ),
          ],
        ),
      ),
    );
  }
}
