import 'dart:async';

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

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Itinerary>? _saved;
  List<Itinerary>? _recent;
  String? _error;
  int _seen = -1;

  static const _savedOnHome = 3;

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
    final state = context.read<AppState>();
    try {
      final results = await Future.wait([state.api.saved(), state.api.recent()]);
      if (state.meta == null) await state.loadMeta();
      if (mounted) {
        setState(() {
          _saved = results[0];
          _recent = results[1];
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  void _openTrip(Itinerary trip, String heroPrefix) {
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => PlanDetailScreen(itineraryId: trip.id, heroTag: tripHeroTag(trip, heroPrefix)),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final cities = state.meta?.cities;
    final first = (state.user?.name ?? '').split(' ').first;
    final shell = ShellScope.of(context);
    final saved = _saved;
    final recent = _error != null ? const <Itinerary>[] : _recent;
    final wide = MediaQuery.sizeOf(context).width >= 900;
    return Scaffold(
      body: RefreshIndicator(
        onRefresh: _load,
        child: CustomScrollView(
          slivers: [
            SliverToBoxAdapter(
              child: _Hero(
                name: first,
                onChat: () => shell.openPlan('chat'),
                onOptions: () => shell.openPlan('options'),
              ),
            ),
            SliverToBoxAdapter(
              child: _Centered(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const SectionTitle('Destinations'),
                    if (cities == null)
                      const Padding(
                        padding: EdgeInsets.symmetric(horizontal: 20),
                        child: Skeleton(height: 300, radius: 28),
                      )
                    else if (cities.isNotEmpty)
                      CityCarousel(
                        cities: cities,
                        onTap: (c) => shell.openPlan('options', cityId: c.id),
                      ),
                    if (recent == null || recent.isNotEmpty) ...[
                      const SectionTitle('Recent trips'),
                      SizedBox(
                        height: 210,
                        child: recent == null
                            ? ListView(
                                scrollDirection: Axis.horizontal,
                                padding: const EdgeInsets.symmetric(horizontal: 20),
                                children: const [
                                  Skeleton(width: 300, height: 210, radius: 28),
                                  SizedBox(width: 14),
                                  Skeleton(width: 300, height: 210, radius: 28),
                                ],
                              )
                            : ListView.separated(
                                scrollDirection: Axis.horizontal,
                                padding: const EdgeInsets.symmetric(horizontal: 20),
                                itemCount: recent.length,
                                separatorBuilder: (_, __) => const SizedBox(width: 14),
                                itemBuilder: (_, i) => SizedBox(
                                  width: 300,
                                  child: Appear(
                                    index: i,
                                    child: TripCard(
                                      trip: recent[i],
                                      showLabel: false,
                                      compact: true,
                                      height: 210,
                                      heroPrefix: 'recent-',
                                      margin: EdgeInsets.zero,
                                      onTap: () => _openTrip(recent[i], 'recent-'),
                                    ),
                                  ),
                                ),
                              ),
                      ),
                    ],
                    SectionTitle(
                      'Saved trips',
                      trailing: (saved?.length ?? 0) > _savedOnHome
                          ? TextButton(onPressed: () => shell.select(AppTab.saved), child: const Text('All'))
                          : null,
                    ),
                    if (_error != null)
                      ErrorRetry(message: _error!, onRetry: _load)
                    else if (saved == null)
                      const SkeletonList(count: 2)
                    else if (saved.isEmpty)
                      EmptyState(
                        image: Media.travelPoster,
                        label: 'No saved trips',
                        action: FilledButton.icon(
                          onPressed: () => shell.openPlan('chat'),
                          icon: const Icon(Icons.explore_outlined),
                          label: const Text('Plan a trip'),
                        ),
                      )
                    else
                      _TripGrid(
                        columns: wide ? 2 : 1,
                        children: [
                          for (var i = 0; i < saved.length.clamp(0, _savedOnHome); i++)
                            Appear(
                              index: i,
                              child: TripCard(
                                trip: saved[i],
                                showLabel: false,
                                height: 230,
                                margin: wide ? const EdgeInsets.all(8) : const EdgeInsets.symmetric(vertical: 8),
                                onTap: () => _openTrip(saved[i], ''),
                              ),
                            ),
                        ],
                      ),
                    const SizedBox(height: 40),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Keeps content at a comfortable reading width on large screens.
class _Centered extends StatelessWidget {
  const _Centered({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Center(child: ConstrainedBox(constraints: const BoxConstraints(maxWidth: 1100), child: child));
  }
}

class _TripGrid extends StatelessWidget {
  const _TripGrid({required this.columns, required this.children});

  final int columns;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    if (columns == 1) {
      return Padding(padding: const EdgeInsets.symmetric(horizontal: 20), child: Column(children: children));
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Wrap(
        children: [
          for (final c in children) FractionallySizedBox(widthFactor: 1 / columns, child: c),
        ],
      ),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.name, required this.onChat, required this.onOptions});

  final String name;
  final VoidCallback onChat;
  final VoidCallback onOptions;

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.sizeOf(context);
    final wide = size.width >= wideBreakpoint;
    final height = (size.height * (wide ? 0.62 : 0.7)).clamp(440.0, 640.0);
    return ClipRRect(
      borderRadius: const BorderRadius.vertical(bottom: Radius.circular(36)),
      child: SizedBox(
        height: height,
        child: Stack(
          fit: StackFit.expand,
          children: [
            const LoopingVideo(video: Media.homeVideo, poster: Media.homePoster),
            DecoratedBox(decoration: BoxDecoration(gradient: Palette.photoShade(top: 0.25, bottom: 0.88, start: 0))),
            SafeArea(
              bottom: false,
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1100),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(24, 8, 8, 30),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            if (!wide) Text('QissaGo', style: display(26, color: Colors.white)),
                            const Spacer(),
                            const ProfileAvatar(light: true),
                          ],
                        ),
                        const Spacer(),
                        if (name.isNotEmpty)
                          Appear(
                            child: Text('Hello, $name',
                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 16)),
                          ),
                        const SizedBox(height: 8),
                        Appear(
                          index: 1,
                          child: Text('Where to next?', style: display(wide ? 64 : 46, color: Colors.white)),
                        ),
                        const SizedBox(height: 24),
                        Appear(
                          index: 2,
                          child: Padding(
                            padding: const EdgeInsets.only(right: 16),
                            child: ConstrainedBox(
                              constraints: const BoxConstraints(maxWidth: 460),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: FilledButton.icon(
                                      onPressed: onChat,
                                      icon: const Icon(Icons.chat_bubble_outline),
                                      label: const Text('Chat'),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: FilledButton.icon(
                                      style: FilledButton.styleFrom(
                                          backgroundColor: Palette.paper, foregroundColor: Palette.slate),
                                      onPressed: onOptions,
                                      icon: const Icon(Icons.tune),
                                      label: const Text('Options'),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Destinations that slide by on their own; swiping or tapping takes over.
class CityCarousel extends StatefulWidget {
  const CityCarousel(
      {super.key, required this.cities, required this.onTap, this.interval = const Duration(seconds: 5)});

  final List<City> cities;
  final ValueChanged<City> onTap;
  final Duration interval;

  @override
  State<CityCarousel> createState() => _CityCarouselState();
}

class _CityCarouselState extends State<CityCarousel> {
  PageController? _pages;
  double _fraction = 0;
  Timer? _timer;
  int _page = 0;
  bool _active = true;

  // Start far from 0 so the carousel can loop in both directions.
  int get _startPage => widget.cities.length * 500;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _active = TickerMode.valuesOf(context).enabled;
    final width = MediaQuery.sizeOf(context).width;
    final fraction = width >= 1100 ? 0.34 : (width >= 700 ? 0.5 : 0.8);
    if (fraction != _fraction) {
      final current = _pages?.hasClients == true ? _pages!.page?.round() ?? _startPage : _startPage;
      _pages?.dispose();
      _fraction = fraction;
      _pages = PageController(viewportFraction: fraction, initialPage: current);
      _page = current;
    }
    _restart();
  }

  void _restart() {
    _timer?.cancel();
    if (MediaQuery.disableAnimationsOf(context) || widget.cities.length < 2) return;
    _timer = Timer.periodic(widget.interval, (_) {
      final p = _pages;
      if (!mounted || p == null || !p.hasClients || !_active) return;
      p.nextPage(duration: const Duration(milliseconds: 700), curve: Curves.easeInOutCubic);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pages?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final n = widget.cities.length;
    final wide = MediaQuery.sizeOf(context).width >= wideBreakpoint;
    return Column(
      children: [
        SizedBox(
          height: wide ? 360 : 320,
          child: NotificationListener<ScrollStartNotification>(
            onNotification: (n) {
              if (n.dragDetails != null) _restart();
              return false;
            },
            child: PageView.builder(
              controller: _pages,
              padEnds: !wide,
              onPageChanged: (i) => setState(() => _page = i),
              itemBuilder: (_, i) {
                final city = widget.cities[i % n];
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: _CityCard(city: city, onTap: () => widget.onTap(city)),
                );
              },
            ),
          ),
        ),
        const SizedBox(height: 12),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            for (var i = 0; i < n; i++)
              AnimatedContainer(
                duration: const Duration(milliseconds: 300),
                margin: const EdgeInsets.symmetric(horizontal: 3),
                width: _page % n == i ? 22 : 8,
                height: 8,
                decoration: BoxDecoration(
                  color: _page % n == i ? Palette.slate : Palette.line,
                  borderRadius: BorderRadius.circular(4),
                ),
              ),
          ],
        ),
      ],
    );
  }
}

class _CityCard extends StatelessWidget {
  const _CityCard({required this.city, required this.onTap});

  final City city;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Palette.sage,
      borderRadius: BorderRadius.circular(28),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Stack(
          fit: StackFit.expand,
          children: [
            NetImage(path: city.image, label: city.name),
            DecoratedBox(decoration: BoxDecoration(gradient: Palette.photoShade(top: 0, bottom: 0.88, start: 0.4))),
            Positioned(
              left: 20,
              right: 20,
              bottom: 20,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (city.province.isNotEmpty)
                    Text(city.province.toUpperCase(),
                        style: const TextStyle(
                            color: Colors.white, fontSize: 11, letterSpacing: 1.4, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 4),
                  Text(city.name, style: display(34, color: Colors.white)),
                  const SizedBox(height: 10),
                  Pill('${city.places} places', icon: Icons.place_outlined, color: Palette.paper),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
