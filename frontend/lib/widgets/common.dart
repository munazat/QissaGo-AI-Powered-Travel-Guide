import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../core/config.dart';
import '../theme.dart';

/// Photo from the backend (downloaded once, then kept in the device cache; on the web the browser caches it).
/// Without a photo it shows a sage gradient with the place's initial.
class NetImage extends StatelessWidget {
  const NetImage({super.key, required this.path, this.label = '', this.fit = BoxFit.cover, this.radius = 0});

  final String path;
  final String label;
  final BoxFit fit;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final fallback = _Placeholder(label: label);
    final url = AppConfig.media(path);
    final child = url.isEmpty
        ? fallback
        : kIsWeb
            // cached_network_image can paint black on web when a carousel recycles the same photo.
            ? Image.network(
                url,
                fit: fit,
                gaplessPlayback: true,
                frameBuilder: (_, child, frame, sync) => sync || frame != null ? child : fallback,
                errorBuilder: (_, __, ___) => fallback,
              )
            : CachedNetworkImage(
                imageUrl: url,
                fit: fit,
                fadeInDuration: const Duration(milliseconds: 250),
                placeholder: (_, __) => fallback,
                errorWidget: (_, __, ___) => fallback,
              );
    return radius == 0 ? child : ClipRRect(borderRadius: BorderRadius.circular(radius), child: child);
  }
}

class _Placeholder extends StatelessWidget {
  const _Placeholder({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Palette.sage, Palette.primary],
        ),
      ),
      alignment: Alignment.center,
      child: label.isEmpty
          ? const Icon(Icons.landscape_outlined, color: Palette.slate, size: 36)
          : Text(label.characters.first.toUpperCase(), style: display(40, color: Palette.slate)),
    );
  }
}

/// Circular match score, e.g. 92 out of 100.
class ScoreRing extends StatelessWidget {
  const ScoreRing({super.key, required this.score, this.size = 56, this.light = false});

  final int score;
  final double size;
  final bool light;

  @override
  Widget build(BuildContext context) {
    final color = light ? Colors.white : Palette.slate;
    final track = light ? Colors.white.withValues(alpha: 0.25) : Palette.sage;
    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          SizedBox(
            width: size,
            height: size,
            child: CircularProgressIndicator(
              value: score.clamp(0, 100) / 100,
              strokeWidth: size / 12,
              backgroundColor: track,
              strokeCap: StrokeCap.round,
              valueColor: const AlwaysStoppedAnimation(Palette.terracotta),
            ),
          ),
          Text('$score', style: TextStyle(fontSize: size * 0.32, fontWeight: FontWeight.w800, color: color)),
        ],
      ),
    );
  }
}

class Pill extends StatelessWidget {
  const Pill(this.text, {super.key, this.icon, this.color = Palette.sage, this.textColor = Palette.onPrimary});

  final String text;
  final IconData? icon;
  final Color color;
  final Color textColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(20)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[Icon(icon, size: 14, color: textColor), const SizedBox(width: 4)],
          Text(text, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: textColor)),
        ],
      ),
    );
  }
}

class SectionTitle extends StatelessWidget {
  const SectionTitle(this.text, {super.key, this.trailing});

  final String text;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 24, 12, 12),
      child: Row(
        children: [
          Expanded(child: Text(text, style: display(24))),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}

IconData weatherIcon(String icon) {
  switch (icon) {
    case 'sunny':
      return Icons.wb_sunny_outlined;
    case 'partly':
      return Icons.wb_cloudy_outlined;
    case 'cloudy':
      return Icons.cloud_outlined;
    case 'fog':
      return Icons.blur_on;
    case 'rain':
      return Icons.umbrella_outlined;
    case 'snow':
      return Icons.ac_unit;
    case 'storm':
      return Icons.thunderstorm;
    default:
      return Icons.wb_sunny_outlined;
  }
}

IconData categoryIcon(String category) {
  switch (category) {
    case 'mosque':
    case 'shrine':
    case 'church':
      return Icons.mosque;
    case 'museum':
    case 'arts centre':
      return Icons.museum_outlined;
    case 'food street':
    case 'dining street':
      return Icons.restaurant_outlined;
    case 'market':
    case 'mall':
      return Icons.shopping_bag_outlined;
    case 'park':
    case 'garden':
    case 'safari park':
    case 'zoo':
      return Icons.park_outlined;
    case 'beach':
    case 'lake':
    case 'island':
      return Icons.waves_outlined;
    case 'hiking trail':
    case 'viewpoint':
    case 'caves':
      return Icons.terrain_outlined;
    case 'amusement park':
      return Icons.attractions_outlined;
    default:
      return Icons.account_balance_outlined;
  }
}

void showError(BuildContext context, Object error) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(error.toString())));
}

class ErrorRetry extends StatelessWidget {
  const ErrorRetry({super.key, required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined, size: 48, color: Palette.muted),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center, style: const TextStyle(color: Palette.muted)),
            const SizedBox(height: 16),
            OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}
