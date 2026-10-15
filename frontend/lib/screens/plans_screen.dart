import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../core/format.dart';
import '../core/models.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/media.dart';
import '../widgets/nav.dart';
import '../widgets/trip_card.dart';
import 'plan_detail_screen.dart';
import 'shell.dart';

/// The three plan options, best match first.
class PlansScreen extends StatefulWidget {
  const PlansScreen({super.key, this.plans, this.batchId, this.source}) : assert(plans != null || batchId != null);

  final List<Itinerary>? plans;
  final String? batchId;

  /// 'chat' or 'options' when the plans were just made; the back button returns there.
  final String? source;

  @override
  State<PlansScreen> createState() => _PlansScreenState();
}

class _PlansScreenState extends State<PlansScreen> {
  List<Itinerary>? _plans;
  String? _error;

  @override
  void initState() {
    super.initState();
    _plans = widget.plans;
    if (_plans == null) _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final plans = await context.read<AppState>().api.batch(widget.batchId!);
      if (mounted) setState(() => _plans = plans);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Widget _backBar() {
    final source = widget.source;
    final shell = ShellScope.maybeOf(context);
    if (source == null || shell == null) return const BackHomeBar(padding: EdgeInsets.fromLTRB(20, 4, 20, 12));
    return BackHomeBar(
      backLabel: source == 'chat' ? 'Back to chat' : 'Back to options',
      padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
      onBack: () => shell.openPlan(source),
    );
  }

  @override
  Widget build(BuildContext context) {
    final plans = _plans;
    final wide = MediaQuery.sizeOf(context).width >= 1100;
    return Scaffold(
      appBar: AppBar(title: Text('Your options', style: display(24))),
      body: _error != null
          ? ErrorRetry(message: _error!, onRetry: _load)
          : Center(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: wide ? 1240 : 760),
                child: ListView(
                  padding: const EdgeInsets.only(bottom: 32),
                  children: [
                    _backBar(),
                    if (plans == null)
                      const SkeletonList(count: 3, height: 260)
                    else ...[
                      if (plans.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
                          child: Text(
                            '${plans.first.cityName}  ·  ${dateRange(plans.first.startDate, plans.first.days)}'
                            '  ·  ${plans.first.people} ${plans.first.people == 1 ? 'person' : 'people'}',
                            style: const TextStyle(color: Palette.muted, fontWeight: FontWeight.w600),
                          ),
                        ),
                      if (wide)
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              for (var i = 0; i < plans.length; i++)
                                Expanded(child: Appear(index: i, child: _card(plans[i], height: 420))),
                            ],
                          ),
                        )
                      else
                        for (var i = 0; i < plans.length; i++) Appear(index: i, child: _card(plans[i])),
                    ],
                  ],
                ),
              ),
            ),
    );
  }

  Widget _card(Itinerary p, {double height = 280}) {
    final wide = height > 300;
    return TripCard(
      trip: p,
      height: height,
      margin: wide ? const EdgeInsets.all(8) : const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      onTap: () async {
        await Navigator.of(context).push(MaterialPageRoute(builder: (_) => PlanDetailScreen(itinerary: p)));
        if (mounted) setState(() {});
      },
    );
  }
}
