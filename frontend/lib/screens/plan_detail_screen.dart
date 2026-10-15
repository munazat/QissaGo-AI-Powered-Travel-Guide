import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:printing/printing.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/app_state.dart';
import '../core/format.dart';
import '../core/models.dart';
import '../core/trip_pdf.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/cost_breakdown.dart';
import '../widgets/media.dart';
import '../widgets/nav.dart';
import '../widgets/trip_card.dart';
import 'plans_screen.dart';

/// One itinerary, day by day. Opened from the options list or from saved trips.
class PlanDetailScreen extends StatefulWidget {
  const PlanDetailScreen({super.key, this.itinerary, this.itineraryId, this.heroTag})
      : assert(itinerary != null || itineraryId != null);

  final Itinerary? itinerary;
  final String? itineraryId;

  /// Tag of the card photo this screen grows out of.
  final String? heroTag;

  @override
  State<PlanDetailScreen> createState() => _PlanDetailScreenState();
}

class _PlanDetailScreenState extends State<PlanDetailScreen> {
  Itinerary? _trip;
  String? _error;
  int _day = 0;
  bool _saving = false;
  bool _exporting = false;

  @override
  void initState() {
    super.initState();
    _trip = widget.itinerary;
    if (_trip == null || !_trip!.hasPlan) _load();
  }

  String get _id => widget.itineraryId ?? widget.itinerary!.id;

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final t = await context.read<AppState>().api.itinerary(_id);
      if (mounted) setState(() => _trip = t);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    }
  }

  Future<void> _toggleSave() async {
    final trip = _trip!;
    setState(() => _saving = true);
    final api = context.read<AppState>().api;
    try {
      if (trip.saved) {
        await api.unsave(trip.id);
      } else {
        await api.save(trip.id);
      }
      if (!mounted) return;
      setState(() => trip.saved = !trip.saved);
      context.read<AppState>().savedChanged();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(trip.saved ? 'Saved' : 'Removed')));
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _downloadPdf() async {
    final trip = _trip;
    if (trip == null || _exporting) return;
    setState(() => _exporting = true);
    try {
      final assets = await loadPdfAssets(trip);
      final bytes = await buildTripPdf(trip, assets);
      await Printing.sharePdf(bytes: bytes, filename: tripPdfName(trip));
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => _exporting = false);
    }
  }

  void _showToggles() {
    showModalBottomSheet(context: context, showDragHandle: true, builder: (_) => const _ToggleSheet());
  }

  @override
  Widget build(BuildContext context) {
    final trip = _trip;
    final heroTag = widget.heroTag ?? (trip != null ? tripHeroTag(trip) : null);
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(),
        body: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [const BackHomeBar(), Expanded(child: ErrorRetry(message: _error!, onRetry: _load))],
        ),
      );
    }
    if (trip == null || !trip.hasPlan) return _LoadingDetail(heroTag: heroTag, trip: trip);

    final show = context.watch<AppState>().show;
    final days = trip.dayPlans;
    final day = days.isEmpty ? null : days[_day.clamp(0, days.length - 1)];
    final width = MediaQuery.sizeOf(context).width;
    final twoColumns = width >= 1100;

    final timeline = day == null
        ? const SizedBox.shrink()
        : Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _DayHeader(day: day, showWeather: show['weather'] ?? true),
              _Timeline(key: ValueKey('${trip.id}-$_day'), day: day, show: show),
            ],
          );
    final mapCard = day != null && (show['map'] ?? true) && day.stops.isNotEmpty
        ? _MapCard(key: ValueKey('map-${trip.id}-$_day'), day: day, height: twoColumns ? 420 : 280)
        : null;

    return Scaffold(
      body: CustomScrollView(
        slivers: [
          _Header(
            trip: trip,
            heroTag: heroTag!,
            saving: _saving,
            exporting: _exporting,
            onSave: _toggleSave,
            onToggles: _showToggles,
            onPdf: _downloadPdf,
          ),
          SliverToBoxAdapter(
            child: _Width(
              max: twoColumns ? 1200 : 760,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                    child: Wrap(
                      spacing: 10,
                      runSpacing: 8,
                      children: [
                        const BackHomeBar(padding: EdgeInsets.zero),
                        _PdfButton(busy: _exporting, onPressed: _downloadPdf),
                      ],
                    ),
                  ),
                  if (!twoColumns)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                      child: Appear(child: CostBreakdown(totals: trip.totals)),
                    ),
                ],
              ),
            ),
          ),
          SliverPersistentHeader(
            pinned: true,
            delegate: _DaySelector(
              days: days,
              selected: _day,
              maxWidth: twoColumns ? 1200 : 760,
              onSelect: (i) => setState(() => _day = i),
            ),
          ),
          SliverToBoxAdapter(
            child: _Width(
              max: twoColumns ? 1200 : 760,
              child: twoColumns
                  ? Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(flex: 6, child: timeline),
                          const SizedBox(width: 16),
                          Expanded(
                            flex: 5,
                            child: Padding(
                              padding: const EdgeInsets.only(top: 12, right: 8),
                              child: Column(
                                children: [
                                  if (mapCard != null) mapCard,
                                  const SizedBox(height: 16),
                                  CostBreakdown(totals: trip.totals),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    )
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        if (mapCard != null) Padding(padding: const EdgeInsets.fromLTRB(16, 12, 16, 0), child: mapCard),
                        timeline,
                      ],
                    ),
            ),
          ),
          SliverToBoxAdapter(
            child: _Width(
              max: 760,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 24, 16, 40),
                child: Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  alignment: WrapAlignment.center,
                  children: [
                    OutlinedButton.icon(
                      onPressed: () => Navigator.of(context)
                          .push(MaterialPageRoute(builder: (_) => PlansScreen(batchId: trip.batchId))),
                      icon: const Icon(Icons.view_carousel_outlined),
                      label: const Text('All options'),
                    ),
                    const BackHomeBar(padding: EdgeInsets.zero),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

Future<void> openLink(String url) async {
  if (url.isEmpty) return;
  await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
}

class _Width extends StatelessWidget {
  const _Width({required this.max, required this.child});

  final double max;
  final Widget child;

  @override
  Widget build(BuildContext context) =>
      Center(child: ConstrainedBox(constraints: BoxConstraints(maxWidth: max), child: child));
}

/// Photo header with title, dates and match score. The photo is the hero from the card.
class _Header extends StatelessWidget {
  const _Header({
    required this.trip,
    required this.heroTag,
    required this.saving,
    required this.exporting,
    required this.onSave,
    required this.onToggles,
    required this.onPdf,
  });

  final Itinerary trip;
  final String heroTag;
  final bool saving;
  final bool exporting;
  final VoidCallback onSave;
  final VoidCallback onToggles;
  final VoidCallback onPdf;

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 700;
    final best = trip.label == 'Best match';
    return SliverAppBar(
      expandedHeight: wide ? 420 : 340,
      pinned: true,
      backgroundColor: Palette.slate,
      foregroundColor: Colors.white,
      title: Text(trip.title, style: display(22, color: Colors.white)),
      actions: [
        IconButton(
            tooltip: 'Download PDF',
            onPressed: exporting ? null : onPdf,
            icon: const Icon(Icons.picture_as_pdf_outlined)),
        IconButton(tooltip: 'Show', onPressed: onToggles, icon: const Icon(Icons.tune)),
        IconButton(
          tooltip: trip.saved ? 'Saved' : 'Save',
          onPressed: saving ? null : onSave,
          icon: Icon(trip.saved ? Icons.bookmark : Icons.bookmark_border),
        ),
        const SizedBox(width: 4),
      ],
      flexibleSpace: FlexibleSpaceBar(
        collapseMode: CollapseMode.parallax,
        background: Stack(
          fit: StackFit.expand,
          children: [
            Hero(tag: heroTag, child: NetImage(path: trip.image, label: trip.cityName)),
            DecoratedBox(decoration: BoxDecoration(gradient: Palette.photoShade(top: 0.35, bottom: 0.92, start: 0))),
            Positioned(
              left: 20,
              right: 20,
              bottom: 22,
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 1160),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            if (trip.label.isNotEmpty)
                              Padding(
                                padding: const EdgeInsets.only(bottom: 10),
                                child: Pill(trip.label,
                                    icon: best ? Icons.star_rounded : null,
                                    color: best ? Palette.terracotta : Palette.paper),
                              ),
                            Text(trip.title, style: display(wide ? 46 : 34, color: Colors.white)),
                            const SizedBox(height: 8),
                            Text(
                              '${trip.cityName}  ·  ${dateRange(trip.startDate, trip.days)}  ·  '
                              '${trip.people} ${trip.people == 1 ? 'person' : 'people'}',
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                            ),
                          ],
                        ),
                      ),
                      ScoreRing(score: trip.matchScore, light: true, size: 64),
                    ],
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

class _PdfButton extends StatelessWidget {
  const _PdfButton({required this.busy, required this.onPressed});

  final bool busy;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return FilledButton.icon(
      style: FilledButton.styleFrom(minimumSize: const Size(0, 48)),
      onPressed: busy ? null : onPressed,
      icon: busy
          ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2.2))
          : const Icon(Icons.picture_as_pdf_outlined),
      label: const Text('Download PDF'),
    );
  }
}

class _LoadingDetail extends StatelessWidget {
  const _LoadingDetail({required this.heroTag, required this.trip});

  final String? heroTag;
  final Itinerary? trip;

  @override
  Widget build(BuildContext context) {
    final photo = trip == null ? const Skeleton(radius: 0) : NetImage(path: trip!.image, label: trip!.cityName);
    return Scaffold(
      appBar: AppBar(backgroundColor: Palette.slate, foregroundColor: Colors.white),
      body: ListView(
        children: [
          SizedBox(height: 260, child: heroTag == null ? photo : Hero(tag: heroTag!, child: photo)),
          const SizedBox(height: 16),
          const Padding(padding: EdgeInsets.symmetric(horizontal: 16), child: Skeleton(height: 160, radius: 28)),
          const SizedBox(height: 16),
          const SkeletonList(count: 3, height: 110),
        ],
      ),
    );
  }
}

/// Day chips that stay pinned under the app bar while the timeline scrolls.
class _DaySelector extends SliverPersistentHeaderDelegate {
  _DaySelector({required this.days, required this.selected, required this.onSelect, required this.maxWidth});

  final List<PlanDay> days;
  final int selected;
  final ValueChanged<int> onSelect;
  final double maxWidth;

  @override
  double get minExtent => 68;

  @override
  double get maxExtent => 68;

  @override
  Widget build(BuildContext context, double shrinkOffset, bool overlapsContent) {
    return Container(
      color: Palette.sand,
      child: Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(maxWidth: maxWidth),
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            children: [
              for (var i = 0; i < days.length; i++)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  child: _DayChip(day: days[i], selected: selected == i, onTap: () => onSelect(i)),
                ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  bool shouldRebuild(_DaySelector old) => old.selected != selected || old.days != days || old.maxWidth != maxWidth;
}

class _DayChip extends StatelessWidget {
  const _DayChip({required this.day, required this.selected, required this.onTap});

  final PlanDay day;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: selected,
      button: true,
      child: Material(
        color: selected ? Palette.primary : Palette.sage,
        shape: const StadiumBorder(),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Text('Day ${day.day}',
                    style: const TextStyle(fontWeight: FontWeight.w800, color: Palette.onPrimary, fontSize: 14)),
                const SizedBox(width: 6),
                Text(day.weekday, style: const TextStyle(color: Palette.onPrimary, fontSize: 13)),
                const SizedBox(width: 6),
                Icon(weatherIcon(day.weather.icon), size: 16, color: Palette.onPrimary),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DayHeader extends StatelessWidget {
  const _DayHeader({required this.day, required this.showWeather});

  final PlanDay day;
  final bool showWeather;

  @override
  Widget build(BuildContext context) {
    final w = day.weather;
    final date = DateTime.tryParse(day.date);
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 18, 16, 8),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(date == null ? 'Day ${day.day}' : longDate(date), style: display(26)),
                const SizedBox(height: 4),
                Text('${day.stops.length} places  ·  ${day.km.toStringAsFixed(1)} km  ·  ${rupees(day.cost)}',
                    style: const TextStyle(color: Palette.muted, fontWeight: FontWeight.w600)),
              ],
            ),
          ),
          if (showWeather)
            Tooltip(
              message: w.text,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(color: Palette.sage, borderRadius: BorderRadius.circular(16)),
                child: Row(
                  children: [
                    Icon(weatherIcon(w.icon), color: Palette.slate, size: 20),
                    const SizedBox(width: 6),
                    Text('${w.tmax}° / ${w.tmin}°', style: const TextStyle(fontWeight: FontWeight.w800)),
                    if (w.rainPct >= 30) ...[
                      const SizedBox(width: 6),
                      const Icon(Icons.water_drop_outlined, size: 14, color: Palette.slate),
                      Text('${w.rainPct}%', style: const TextStyle(fontWeight: FontWeight.w600)),
                    ],
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// Map of the day's stops, numbered like the timeline, with a button for turn-by-turn directions.
class _MapCard extends StatelessWidget {
  const _MapCard({super.key, required this.day, required this.height});

  final PlanDay day;
  final double height;

  @override
  Widget build(BuildContext context) {
    final points = [for (final s in day.stops) LatLng(s.lat, s.lon)];
    return Container(
      height: height,
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        boxShadow: [
          BoxShadow(color: Palette.slate.withValues(alpha: 0.18), blurRadius: 18, offset: const Offset(0, 8))
        ],
      ),
      child: Stack(
        children: [
          FlutterMap(
            options: MapOptions(
              initialCenter: points.first,
              initialZoom: 14,
              initialCameraFit: points.length > 1
                  ? CameraFit.bounds(bounds: LatLngBounds.fromPoints(points), padding: const EdgeInsets.all(48))
                  : null,
              interactionOptions: const InteractionOptions(flags: InteractiveFlag.all & ~InteractiveFlag.rotate),
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'com.qissago.app',
              ),
              PolylineLayer(
                polylines: [
                  Polyline(
                    points: points,
                    strokeWidth: 5,
                    color: Palette.primary,
                    borderStrokeWidth: 2,
                    borderColor: Palette.slate,
                  ),
                ],
              ),
              MarkerLayer(
                markers: [
                  for (var i = 0; i < points.length; i++)
                    Marker(point: points[i], width: 32, height: 32, child: _StopNumber(i + 1, size: 32)),
                ],
              ),
            ],
          ),
          Positioned(
            left: 12,
            top: 12,
            child: Pill('${day.stops.length} places  ·  ${day.km.toStringAsFixed(1)} km',
                icon: Icons.route_outlined, color: Palette.paper),
          ),
          if (day.routeUrl.isNotEmpty)
            Positioned(
              right: 12,
              top: 8,
              child: FilledButton.icon(
                style: FilledButton.styleFrom(minimumSize: const Size(0, 40)),
                onPressed: () => openLink(day.routeUrl),
                icon: const Icon(Icons.directions_outlined, size: 18),
                label: const Text('Route'),
              ),
            ),
          Positioned(
            right: 10,
            bottom: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              color: Palette.paper.withValues(alpha: 0.85),
              child: const Text('© OpenStreetMap contributors', style: TextStyle(fontSize: 10, color: Palette.slate)),
            ),
          ),
        ],
      ),
    );
  }
}

class _StopNumber extends StatelessWidget {
  const _StopNumber(this.number, {this.size = 30});

  final int number;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: Palette.slate,
        shape: BoxShape.circle,
        border: Border.all(color: Palette.paper, width: 2.5),
      ),
      child: Text('$number', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: size * 0.42)),
    );
  }
}

/// The day as a vertical line with numbered stops, meals and breaks, and the travel between them.
class _Timeline extends StatelessWidget {
  const _Timeline({super.key, required this.day, required this.show});

  final PlanDay day;
  final Map<String, bool> show;

  @override
  Widget build(BuildContext context) {
    final rows = <Widget>[];
    var stop = 0;
    final items = day.items;
    for (var i = 0; i < items.length; i++) {
      final item = items[i];
      final first = i == 0;
      final last = i == items.length - 1;
      final leg = item.leg;
      if (item.isStop && leg != null && (show['travel'] ?? true) && !first) {
        rows.add(_Rail(
          marker: const Icon(Icons.directions_car_outlined, size: 16, color: Palette.primaryDeep),
          markerTop: 6,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Text(
              [
                duration(leg.minutes),
                '${leg.km.toStringAsFixed(1)} km',
                if (show['price'] ?? true) leg.byJeep ? 'Jeep' : rupees(leg.cost),
              ].join('  ·  '),
              style: const TextStyle(color: Palette.primaryDeep, fontWeight: FontWeight.w700, fontSize: 13),
            ),
          ),
        ));
      }
      if (item.isStop) {
        stop++;
        rows.add(_Rail(
          top: first,
          bottom: last,
          marker: _StopNumber(stop),
          markerTop: 20,
          child: Appear(index: stop, child: _StopCard(item: item, show: show)),
        ));
      } else {
        rows.add(_Rail(
          top: first,
          bottom: last,
          marker: Container(
            width: 26,
            height: 26,
            decoration: const BoxDecoration(color: Palette.sage, shape: BoxShape.circle),
            child: Icon(item.type == 'lunch' ? Icons.restaurant_outlined : Icons.self_improvement,
                size: 15, color: Palette.slate),
          ),
          markerTop: 10,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Row(
              children: [
                Text(item.name, style: const TextStyle(color: Palette.muted, fontWeight: FontWeight.w700)),
                const Spacer(),
                if (show['time'] ?? true)
                  Text('${item.start} – ${item.end}', style: const TextStyle(color: Palette.muted)),
              ],
            ),
          ),
        ));
      }
    }
    return Padding(padding: const EdgeInsets.fromLTRB(8, 4, 16, 8), child: Column(children: rows));
  }
}

/// One row of the timeline: the line and its marker on the left, content on the right.
class _Rail extends StatelessWidget {
  const _Rail({required this.marker, required this.child, this.markerTop = 12, this.top = false, this.bottom = false});

  final Widget marker;
  final Widget child;
  final double markerTop;
  final bool top;
  final bool bottom;

  static const width = 52.0;

  @override
  Widget build(BuildContext context) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: width,
            child: Stack(
              alignment: Alignment.topCenter,
              children: [
                Positioned(
                  top: top ? markerTop + 10 : 0,
                  bottom: bottom ? null : 0,
                  height: bottom ? markerTop + 10 : null,
                  child: Container(width: 2.5, color: Palette.line),
                ),
                Positioned(top: markerTop, child: marker),
              ],
            ),
          ),
          Expanded(child: child),
        ],
      ),
    );
  }
}

class _StopCard extends StatelessWidget {
  const _StopCard({required this.item, required this.show});

  final PlanItem item;
  final Map<String, bool> show;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Material(
        color: Palette.paper,
        borderRadius: BorderRadius.circular(24),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () => showModalBottomSheet(
            context: context,
            isScrollControlled: true,
            showDragHandle: true,
            builder: (_) => _StopSheet(item: item),
          ),
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (show['photos'] ?? true) ...[
                  SizedBox(width: 100, height: 100, child: NetImage(path: item.image, label: item.name, radius: 18)),
                  const SizedBox(width: 14),
                ],
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (show['time'] ?? true)
                          Text('${item.start} – ${item.end}',
                              style: const TextStyle(
                                  color: Palette.primaryDeep, fontWeight: FontWeight.w800, fontSize: 13)),
                        const SizedBox(height: 2),
                        Text(item.name, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 6,
                          runSpacing: 6,
                          children: [
                            Pill(titleCase(item.category), icon: categoryIcon(item.category)),
                            Pill(duration(item.minutes), icon: Icons.timer_outlined),
                            if (show['price'] ?? true)
                              Pill(item.costGroup == 0 ? 'Free' : rupees(item.costGroup),
                                  icon: Icons.payments_outlined),
                            if ((show['weather'] ?? true) && item.weatherNote.isNotEmpty)
                              Pill(item.weatherNote, icon: Icons.thermostat_outlined, color: Palette.terracotta),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _StopSheet extends StatelessWidget {
  const _StopSheet({required this.item});

  final PlanItem item;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.85, maxWidth: 720),
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                  height: 240, width: double.infinity, child: NetImage(path: item.image, label: item.name, radius: 24)),
              if (item.imageCredit.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text('Photo: ${item.imageCredit}',
                      style: const TextStyle(fontSize: 11, color: Palette.muted),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis),
                ),
              const SizedBox(height: 14),
              Text(item.name, style: display(32)),
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  Pill('${item.open} – ${item.close}', icon: Icons.access_time),
                  Pill(item.outdoor ? 'Outdoor' : 'Indoor',
                      icon: item.outdoor ? Icons.park_outlined : Icons.home_outlined),
                  for (final t in item.tags) Pill(titleCase(t)),
                ],
              ),
              if (item.description.isNotEmpty) ...[
                const SizedBox(height: 16),
                Text(item.description, style: const TextStyle(height: 1.55, fontSize: 15)),
              ],
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: () => openLink(item.mapUrl),
                      icon: const Icon(Icons.map_outlined),
                      label: const Text('Google Maps'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => openLink(item.osmUrl),
                      icon: const Icon(Icons.public),
                      label: const Text('OpenStreetMap'),
                    ),
                  ),
                ],
              ),
              if (item.wikiUrl.isNotEmpty)
                TextButton(onPressed: () => openLink(item.wikiUrl), child: const Text('Wikipedia')),
            ],
          ),
        ),
      ),
    );
  }
}

class _ToggleSheet extends StatelessWidget {
  const _ToggleSheet();

  static const labels = {
    'time': 'Times',
    'travel': 'Travel',
    'price': 'Prices',
    'weather': 'Weather',
    'map': 'Map',
    'photos': 'Photos',
  };

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    return SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final e in labels.entries)
            SwitchListTile(
              title: Text(e.value, style: const TextStyle(fontWeight: FontWeight.w600)),
              value: state.show[e.key] ?? true,
              onChanged: (v) => state.setShow(e.key, v),
            ),
          const SizedBox(height: 12),
        ],
      ),
    );
  }
}
