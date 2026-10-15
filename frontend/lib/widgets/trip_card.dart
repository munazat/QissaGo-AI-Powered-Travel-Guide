import 'package:flutter/material.dart';

import '../core/format.dart';
import '../core/models.dart';
import '../theme.dart';
import 'common.dart';

/// Hero tag shared by a trip's card photo and the plan detail header.
String tripHeroTag(Itinerary trip, [String prefix = '']) => '${prefix}trip-photo-${trip.id}';

/// Big photo card for one itinerary (used for the 3 options and for saved trips).
class TripCard extends StatelessWidget {
  const TripCard({
    super.key,
    required this.trip,
    required this.onTap,
    this.showLabel = true,
    this.height = 260,
    this.margin = const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
    this.compact = false,
    this.heroPrefix = '',
  });

  final Itinerary trip;
  final VoidCallback onTap;
  final bool showLabel;
  final double height;
  final EdgeInsets margin;

  /// Smaller text for horizontal rows.
  final bool compact;

  /// Keeps hero tags unique when the same trip is listed twice on one screen.
  final String heroPrefix;

  @override
  Widget build(BuildContext context) {
    final best = trip.label == 'Best match';
    return Padding(
      padding: margin,
      child: Material(
        color: Palette.sage,
        borderRadius: BorderRadius.circular(28),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: SizedBox(
            height: height,
            child: Stack(
              fit: StackFit.expand,
              children: [
                Hero(tag: tripHeroTag(trip, heroPrefix), child: NetImage(path: trip.image, label: trip.cityName)),
                DecoratedBox(decoration: BoxDecoration(gradient: Palette.photoShade(top: 0, bottom: 0.92, start: 0.3))),
                Positioned(
                  top: 14,
                  left: 14,
                  right: 14,
                  child: Row(
                    children: [
                      if (showLabel && trip.label.isNotEmpty)
                        Pill(
                          trip.label,
                          icon: best ? Icons.star_rounded : null,
                          color: best ? Palette.terracotta : Palette.paper,
                          textColor: Palette.onPrimary,
                        ),
                      const Spacer(),
                      if (trip.saved)
                        const CircleAvatar(
                          radius: 16,
                          backgroundColor: Palette.paper,
                          child: Icon(Icons.bookmark, size: 18, color: Palette.slate),
                        ),
                    ],
                  ),
                ),
                Positioned(
                  left: compact ? 16 : 20,
                  right: compact ? 16 : 20,
                  bottom: compact ? 14 : 18,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(trip.title,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: display(compact ? 22 : 28, color: Colors.white)),
                            const SizedBox(height: 6),
                            Text(
                              '${trip.cityName}  ·  ${dateRange(trip.startDate, trip.days)}',
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                            ),
                            const SizedBox(height: 10),
                            Wrap(
                              spacing: 8,
                              runSpacing: 6,
                              children: [
                                Pill(rupees(trip.totalCost), icon: Icons.payments_outlined, color: Palette.paper),
                                if (trip.hasPlan && !compact)
                                  Pill('${trip.stopCount} places', icon: Icons.place_outlined, color: Palette.paper),
                                if (trip.hasPlan && !compact)
                                  Pill('${trip.km.toStringAsFixed(0)} km',
                                      icon: Icons.route_outlined, color: Palette.paper),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      ScoreRing(score: trip.matchScore, light: true, size: compact ? 48 : 58),
                    ],
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
