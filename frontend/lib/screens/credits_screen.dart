import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../core/credits.dart';
import '../theme.dart';
import '../widgets/nav.dart';
import 'plan_detail_screen.dart' show openLink;

/// Where every bundled photo and video comes from, with author and licence.
class CreditsScreen extends StatefulWidget {
  const CreditsScreen({super.key, this.bundle});

  /// Tests pass their own bundle.
  final AssetBundle? bundle;

  @override
  State<CreditsScreen> createState() => _CreditsScreenState();
}

class _CreditsScreenState extends State<CreditsScreen> {
  List<Credit>? _credits;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final text = await (widget.bundle ?? rootBundle).loadString('assets/credits.csv');
    // Each clip and its still share a source; list the clip once.
    final seen = <String>{};
    final list = parseCredits(text).where((c) => seen.add(c.sourceUrl)).toList();
    if (mounted) setState(() => _credits = list);
  }

  @override
  Widget build(BuildContext context) {
    final credits = _credits;
    return Scaffold(
      appBar: AppBar(title: Text('Credits', style: display(24))),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 640),
          child: ListView(
            padding: const EdgeInsets.only(bottom: 32),
            children: [
              const BackHomeBar(),
              if (credits != null)
                for (final c in credits)
                  ListTile(
                    leading: Icon(
                      c.isVideo
                          ? Icons.movie_outlined
                          : (c.file.endsWith('.ttf') ? Icons.text_fields : Icons.photo_outlined),
                      color: Palette.slate,
                    ),
                    title: Text(c.title, style: const TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: Text('${c.author}  ·  ${c.licence}', style: const TextStyle(color: Palette.muted)),
                    trailing: const Icon(Icons.open_in_new, size: 18, color: Palette.muted),
                    onTap: () => openLink(c.sourceUrl),
                  ),
              const ListTile(
                leading: Icon(Icons.place_outlined, color: Palette.slate),
                title: Text('Place photos', style: TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text('Wikimedia Commons', style: TextStyle(color: Palette.muted)),
              ),
              const ListTile(
                leading: Icon(Icons.map_outlined, color: Palette.slate),
                title: Text('Maps', style: TextStyle(fontWeight: FontWeight.w700)),
                subtitle: Text('© OpenStreetMap contributors', style: TextStyle(color: Palette.muted)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
