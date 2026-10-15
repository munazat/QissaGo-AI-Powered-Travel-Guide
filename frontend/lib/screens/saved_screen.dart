import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../core/models.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/media.dart';
import '../widgets/trip_card.dart';
import 'plan_detail_screen.dart';
import 'shell.dart';

/// Saved tab: every trip the user bookmarked.
class SavedScreen extends StatefulWidget {
  const SavedScreen({super.key});

  @override
  State<SavedScreen> createState() => _SavedScreenState();
}

class _SavedScreenState extends State<SavedScreen> {
  List<Itinerary>? _saved;
  String? _error;
  int _seen = -1;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final version = context.watch<AppState>().savedVersion;
    if (version != _seen) {
      _seen = version;
      _load();
    }
  }

  Future<void> _load() async {
    try {
      final saved = await context.read<AppState>().api.saved();
      if (mounted) {
        setState(() {
          _saved = saved;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  @override
  Widget build(BuildContext context) {
    final saved = _saved;
    return Scaffold(
      appBar: AppBar(title: Text('Saved', style: display(24)), actions: const [ProfileAvatar()]),
      body: _error != null
          ? ErrorRetry(message: _error!, onRetry: _load)
          : saved == null
              ? ListView(children: const [SizedBox(height: 8), SkeletonList(count: 3)])
              : RefreshIndicator(
                  onRefresh: _load,
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 760),
                      child: saved.isEmpty
                          ? ListView(
                              children: [
                                const SizedBox(height: 8),
                                EmptyState(
                                  image: Media.travelPoster,
                                  label: 'No saved trips',
                                  height: 360,
                                  action: FilledButton.icon(
                                    onPressed: () => ShellScope.maybeOf(context)?.openPlan('chat'),
                                    icon: const Icon(Icons.explore_outlined),
                                    label: const Text('Plan a trip'),
                                  ),
                                ),
                              ],
                            )
                          : ListView.builder(
                              padding: const EdgeInsets.only(bottom: 32),
                              itemCount: saved.length,
                              itemBuilder: (_, i) => Appear(
                                index: i,
                                child: TripCard(
                                  trip: saved[i],
                                  showLabel: false,
                                  height: 230,
                                  onTap: () => Navigator.of(context).push(
                                      MaterialPageRoute(builder: (_) => PlanDetailScreen(itineraryId: saved[i].id))),
                                ),
                              ),
                            ),
                    ),
                  ),
                ),
    );
  }
}
