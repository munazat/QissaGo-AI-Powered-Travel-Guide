import 'package:flutter/material.dart';

import '../theme.dart';
import 'chat_screen.dart';
import 'quick_plan_screen.dart';
import 'shell.dart';

/// Plan tab: chat or quick options. Both stay alive while switching.
class PlanHubScreen extends StatelessWidget {
  const PlanHubScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final shell = ShellScope.of(context);
    final mode = shell.planMode;
    return Scaffold(
      appBar: AppBar(
        title: Text('Plan', style: display(24)),
        actions: const [ProfileAvatar()],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(60),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
            child: SizedBox(
              width: 360,
              child: SegmentedButton<String>(
                showSelectedIcon: false,
                segments: const [
                  ButtonSegment(value: 'chat', label: Text('Chat'), icon: Icon(Icons.chat_bubble_outline)),
                  ButtonSegment(value: 'options', label: Text('Options'), icon: Icon(Icons.tune)),
                ],
                selected: {mode},
                onSelectionChanged: (s) => shell.setPlanMode(s.first),
              ),
            ),
          ),
        ),
      ),
      body: IndexedStack(
        index: mode == 'options' ? 1 : 0,
        children: [
          const ChatScreen(embedded: true),
          QuickPlanScreen(key: ValueKey(shell.planVersion), cityId: shell.planCity, embedded: true),
        ],
      ),
    );
  }
}
