import 'package:flutter/material.dart';

import '../theme.dart';
import '../widgets/media.dart';
import '../widgets/nav.dart';
import 'shell.dart';

/// Full-screen looping video and title for a tab that comes in a later iteration.
class SoonScreen extends StatelessWidget {
  const SoonScreen({super.key, required this.tab});

  final AppTab tab;

  @override
  Widget build(BuildContext context) {
    final video = tab == AppTab.video;
    final shell = ShellScope.maybeOf(context);
    final wide = MediaQuery.sizeOf(context).width >= wideBreakpoint;
    return Scaffold(
      backgroundColor: Palette.slate,
      body: Stack(
        fit: StackFit.expand,
        children: [
          LoopingVideo(
            video: video ? Media.travelVideo : Media.narrationVideo,
            poster: video ? Media.travelPoster : Media.narrationPoster,
          ),
          DecoratedBox(decoration: BoxDecoration(gradient: Palette.photoShade(top: 0.1, bottom: 0.9, start: 0.35))),
          const SafeArea(child: Align(alignment: Alignment.topRight, child: ProfileAvatar(light: true))),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(28, 24, 28, 36),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Appear(child: SoonBadge()),
                  const SizedBox(height: 12),
                  Appear(index: 1, child: Text(tab.wideLabel, style: display(wide ? 80 : 54, color: Colors.white))),
                  if (shell != null) ...[
                    const SizedBox(height: 24),
                    Appear(
                      index: 2,
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(backgroundColor: Palette.paper, foregroundColor: Palette.slate),
                        onPressed: shell.goHome,
                        icon: const Icon(Icons.home_outlined),
                        label: const Text('Home'),
                      ),
                    ),
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
