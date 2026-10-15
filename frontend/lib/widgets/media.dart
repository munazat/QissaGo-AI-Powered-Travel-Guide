import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import '../theme.dart';

/// Widget tests switch this off; the still image is shown instead.
bool videosEnabled = true;

/// Whether a muted background video may start.
///
/// The clips are bundled with the app, so on Android they cost no data and always play.
/// On the web they are downloaded, so they wait for Wi-Fi or a wired connection.
/// Nobody gets moving backgrounds when the system asks for reduced motion.
bool canAutoplay({required bool isWeb, required List<ConnectivityResult> connection, required bool reduceMotion}) {
  if (reduceMotion) return false;
  if (!isWeb) return true;
  return connection.contains(ConnectivityResult.wifi) ||
      connection.contains(ConnectivityResult.ethernet) ||
      connection.contains(ConnectivityResult.other);
}

/// Muted looping video from the app's assets, with a still image underneath until it is ready
/// (and instead of it when it should not play). Pauses when its tab is hidden.
class LoopingVideo extends StatefulWidget {
  const LoopingVideo({super.key, required this.video, required this.poster, this.alignment = Alignment.center});

  final String video;
  final String poster;
  final Alignment alignment;

  @override
  State<LoopingVideo> createState() => _LoopingVideoState();
}

class _LoopingVideoState extends State<LoopingVideo> {
  VideoPlayerController? _controller;
  bool _ready = false;
  bool _started = false;
  bool _active = true;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _active = TickerMode.valuesOf(context).enabled;
    if (!_started) {
      _started = true;
      _start(MediaQuery.disableAnimationsOf(context));
    }
    _syncPlayback();
  }

  void _syncPlayback() {
    final c = _controller;
    if (c == null || !_ready) return;
    if (_active) {
      c.play();
    } else {
      c.pause();
    }
  }

  Future<void> _start(bool reduceMotion) async {
    if (!videosEnabled) return;
    List<ConnectivityResult> connection;
    try {
      connection = await Connectivity().checkConnectivity();
    } catch (_) {
      connection = const [ConnectivityResult.other];
    }
    if (!canAutoplay(isWeb: kIsWeb, connection: connection, reduceMotion: reduceMotion)) return;
    final c = VideoPlayerController.asset(widget.video, videoPlayerOptions: VideoPlayerOptions(mixWithOthers: true));
    try {
      await c.initialize();
      await c.setVolume(0);
      await c.setLooping(true);
    } catch (_) {
      await c.dispose();
      return;
    }
    if (!mounted) {
      await c.dispose();
      return;
    }
    setState(() {
      _controller = c;
      _ready = true;
    });
    _syncPlayback();
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final c = _controller;
    return Stack(
      fit: StackFit.expand,
      children: [
        Image.asset(widget.poster, fit: BoxFit.cover, alignment: widget.alignment, gaplessPlayback: true),
        if (c != null)
          AnimatedOpacity(
            opacity: _ready ? 1 : 0,
            duration: const Duration(milliseconds: 600),
            child: ClipRect(
              child: FittedBox(
                fit: BoxFit.cover,
                alignment: widget.alignment,
                child: SizedBox(width: c.value.size.width, height: c.value.size.height, child: VideoPlayer(c)),
              ),
            ),
          ),
      ],
    );
  }
}

/// Fades and slides a child in when it first appears. Later items in a list start a little later.
class Appear extends StatelessWidget {
  const Appear({super.key, required this.child, this.index = 0, this.offset = 24});

  final Widget child;
  final int index;
  final double offset;

  @override
  Widget build(BuildContext context) {
    if (MediaQuery.disableAnimationsOf(context)) return child;
    final delay = (index.clamp(0, 8)) * 70;
    final total = 420 + delay;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: total),
      curve: Interval(delay / total, 1, curve: Curves.easeOutCubic),
      builder: (_, t, child) => Opacity(
        opacity: t,
        child: Transform.translate(offset: Offset(0, (1 - t) * offset), child: child),
      ),
      child: child,
    );
  }
}

/// Grey shimmering block shown while content loads.
class Skeleton extends StatefulWidget {
  const Skeleton({super.key, this.width, this.height, this.radius = 16});

  final double? width;
  final double? height;
  final double radius;

  @override
  State<Skeleton> createState() => _SkeletonState();
}

class _SkeletonState extends State<Skeleton> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 1400))
    ..repeat();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (_, __) {
        final x = _c.value * 3 - 1.5;
        return Container(
          width: widget.width,
          height: widget.height,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(widget.radius),
            gradient: LinearGradient(
              begin: Alignment(x - 1, -0.3),
              end: Alignment(x + 1, 0.3),
              colors: const [Palette.sage, Color(0xFFDCE3D6), Palette.sage],
            ),
          ),
        );
      },
    );
  }
}

/// A vertical list of card-shaped skeletons.
class SkeletonList extends StatelessWidget {
  const SkeletonList({super.key, this.count = 3, this.height = 220});

  final int count;
  final double height;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        for (var i = 0; i < count; i++)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
            child: Skeleton(height: height, radius: 28),
          ),
      ],
    );
  }
}

/// Picture with a short label, for lists that have nothing in them yet.
class EmptyState extends StatelessWidget {
  const EmptyState({super.key, required this.image, required this.label, this.action, this.height = 220});

  final String image;
  final String label;
  final Widget? action;
  final double height;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(28),
        child: SizedBox(
          height: height,
          child: Stack(
            fit: StackFit.expand,
            children: [
              Image.asset(image, fit: BoxFit.cover),
              DecoratedBox(decoration: BoxDecoration(gradient: Palette.photoShade(top: 0.1, bottom: 0.85))),
              Padding(
                padding: const EdgeInsets.all(22),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.end,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label, style: display(28, color: Colors.white)),
                    if (action != null) ...[const SizedBox(height: 14), action!],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Bundled media used across the app. Sources and licences are in assets/credits.csv.
class Media {
  static const homeVideo = 'assets/video/home_hero.mp4';
  static const homePoster = 'assets/images/home_hero.jpg';
  static const loginVideo = 'assets/video/login.mp4';
  static const loginPoster = 'assets/images/login.jpg';
  static const travelVideo = 'assets/video/travel_video.mp4';
  static const travelPoster = 'assets/images/travel_video.jpg';
  static const narrationVideo = 'assets/video/narration.mp4';
  static const narrationPoster = 'assets/images/narration.jpg';
}
