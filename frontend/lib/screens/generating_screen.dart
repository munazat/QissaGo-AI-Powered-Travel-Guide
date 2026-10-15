import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../core/models.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/media.dart';
import '../widgets/nav.dart';
import 'plans_screen.dart';

/// Calls the multi-agent planner and shows each agent's step while it works.
class GeneratingScreen extends StatefulWidget {
  const GeneratingScreen({super.key, this.sessionId, this.preferences, this.source});

  final String? sessionId;
  final Map<String, dynamic>? preferences;

  /// 'chat' or 'options': where the plans screen's back button returns to.
  final String? source;

  @override
  State<GeneratingScreen> createState() => _GeneratingScreenState();
}

class _GeneratingScreenState extends State<GeneratingScreen> {
  static const steps = [
    ('Intake', Icons.assignment_outlined),
    ('Weather', Icons.wb_sunny_outlined),
    ('Destinations', Icons.place_outlined),
    ('Budget', Icons.payments_outlined),
    ('Scheduling', Icons.schedule),
    ('Validation', Icons.verified_outlined),
    ('Details', Icons.layers_outlined),
    ('Ranking', Icons.leaderboard_outlined),
  ];

  int _done = 0;
  Timer? _timer;
  String? _error;

  @override
  void initState() {
    super.initState();
    _run();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _run() async {
    setState(() {
      _error = null;
      _done = 0;
    });
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(milliseconds: 320), (t) {
      if (_done < steps.length - 1) setState(() => _done++);
    });
    try {
      final api = context.read<AppState>().api;
      final results = await Future.wait<Object?>([
        api.generate(sessionId: widget.sessionId, preferences: widget.preferences),
        Future.delayed(const Duration(milliseconds: 2400)),
      ]);
      final plans = results.first as List<Itinerary>;
      _timer?.cancel();
      if (!mounted) return;
      setState(() => _done = steps.length);
      await Future.delayed(const Duration(milliseconds: 300));
      if (!mounted) return;
      Navigator.of(context)
          .pushReplacement(MaterialPageRoute(builder: (_) => PlansScreen(plans: plans, source: widget.source)));
    } catch (e) {
      _timer?.cancel();
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Palette.slate,
      body: Stack(
        fit: StackFit.expand,
        children: [
          Image.asset(Media.travelPoster, fit: BoxFit.cover),
          DecoratedBox(decoration: BoxDecoration(color: Palette.slate.withValues(alpha: 0.82))),
          SafeArea(
            child: _error != null
                ? Container(
                    color: Palette.sand,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const BackHomeBar(),
                        Expanded(child: ErrorRetry(message: _error!, onRetry: _run)),
                      ],
                    ),
                  )
                : Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 420),
                      child: Padding(
                        padding: const EdgeInsets.all(28),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('Planning your trip', style: display(36, color: Colors.white)),
                            const SizedBox(height: 28),
                            for (var i = 0; i < steps.length; i++)
                              _StepRow(steps[i].$1, steps[i].$2, i < _done, i == _done),
                          ],
                        ),
                      ),
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

class _StepRow extends StatelessWidget {
  const _StepRow(this.label, this.icon, this.done, this.active);

  final String label;
  final IconData icon;
  final bool done;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final color = done || active ? Colors.white : Colors.white60;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        children: [
          AnimatedContainer(
            duration: const Duration(milliseconds: 250),
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: done ? Palette.terracotta : Colors.white.withValues(alpha: active ? 0.22 : 0.1),
            ),
            child: Icon(done ? Icons.check : icon, size: 18, color: done ? Palette.onPrimary : color),
          ),
          const SizedBox(width: 14),
          Text(label, style: TextStyle(color: color, fontSize: 16, fontWeight: FontWeight.w600)),
          const Spacer(),
          if (active)
            const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
            ),
        ],
      ),
    );
  }
}
