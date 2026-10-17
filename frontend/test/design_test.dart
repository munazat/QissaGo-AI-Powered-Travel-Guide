import 'dart:io';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:qissago/core/credits.dart';
import 'package:qissago/core/models.dart';
import 'package:qissago/screens/chat_screen.dart';
import 'package:qissago/screens/home_screen.dart';
import 'package:qissago/screens/plan_detail_screen.dart';
import 'package:qissago/screens/shell.dart';
import 'package:qissago/theme.dart';
import 'package:qissago/widgets/cost_breakdown.dart';
import 'package:qissago/widgets/media.dart';

import 'helpers.dart';
import 'models_test.dart' show samplePlan;

double contrast(Color a, Color b) {
  final la = a.computeLuminance(), lb = b.computeLuminance();
  final hi = la > lb ? la : lb, lo = la > lb ? lb : la;
  return (hi + 0.05) / (lo + 0.05);
}

void main() {
  group('palette', () {
    test('uses the five brand colours', () {
      expect(Palette.primary, const Color(0xFF8FBC8F));
      expect(Palette.slate, const Color(0xFF2F4F4F));
      expect(Palette.sand, const Color(0xFFE8E4D8));
      expect(Palette.sage, const Color(0xFFC7D3C0));
      expect(Palette.terracotta, const Color(0xFFD9A38F));
    });

    test('text colours are readable (at least 4.5:1)', () {
      expect(contrast(Palette.slate, Palette.sand), greaterThanOrEqualTo(4.5));
      expect(contrast(Palette.slate, Palette.paper), greaterThanOrEqualTo(4.5));
      expect(contrast(Palette.muted, Palette.sand), greaterThanOrEqualTo(4.5));
      expect(contrast(Palette.muted, Palette.sage), greaterThanOrEqualTo(4.5));
      expect(contrast(Palette.onPrimary, Palette.primary), greaterThanOrEqualTo(4.5));
      expect(contrast(Palette.onPrimary, Palette.terracotta), greaterThanOrEqualTo(4.5));
      expect(contrast(Palette.onPrimary, Palette.sage), greaterThanOrEqualTo(4.5));
      expect(contrast(Palette.primaryDeep, Palette.sand), greaterThanOrEqualTo(4.5));
      expect(contrast(Colors.white, Palette.slate), greaterThanOrEqualTo(4.5));
    });

    test('white text on sea green is too light, which is why buttons use dark text', () {
      expect(contrast(Colors.white, Palette.primary), lessThan(4.5));
      final button = buildTheme(useGoogleFonts: false).filledButtonTheme.style!;
      expect(button.foregroundColor!.resolve({}), Palette.onPrimary);
    });
  });

  group('background video', () {
    test('never plays when reduced motion is on', () {
      expect(canAutoplay(isWeb: false, connection: [ConnectivityResult.wifi], reduceMotion: true), false);
    });

    test('always plays on the phone because the clips are bundled', () {
      expect(canAutoplay(isWeb: false, connection: [ConnectivityResult.mobile], reduceMotion: false), true);
    });

    test('on the web waits for Wi-Fi or a wired connection', () {
      expect(canAutoplay(isWeb: true, connection: [ConnectivityResult.mobile], reduceMotion: false), false);
      expect(canAutoplay(isWeb: true, connection: [ConnectivityResult.none], reduceMotion: false), false);
      expect(canAutoplay(isWeb: true, connection: [ConnectivityResult.wifi], reduceMotion: false), true);
      expect(canAutoplay(isWeb: true, connection: [ConnectivityResult.ethernet], reduceMotion: false), true);
    });

    testWidgets('shows the still image when video is off', (tester) async {
      videosEnabled = false;
      await tester.pumpWidget(const MaterialApp(
        home: LoopingVideo(video: Media.homeVideo, poster: Media.homePoster),
      ));
      final image = tester.widget<Image>(find.byType(Image));
      expect((image.image as AssetImage).assetName, Media.homePoster);
    });
  });

  group('credits', () {
    test('CSV parser handles quotes, commas and blank lines', () {
      final rows = parseCsv('a,b,c\n"x, y","he said ""hi""",z\r\n\n');
      expect(rows, [
        ['a', 'b', 'c'],
        ['x, y', 'he said "hi"', 'z'],
      ]);
    });

    test('every bundled image, video and font has a source, author and licence', () {
      final credits = parseCredits(File('assets/credits.csv').readAsStringSync());
      final byFile = {for (final c in credits) c.file: c};
      final files = [
        ...Directory('assets/images').listSync(),
        ...Directory('assets/video').listSync(),
        ...Directory('assets/fonts').listSync().where((f) => f.path.endsWith('.ttf')),
      ].whereType<File>().map((f) => f.path.replaceAll('\\', '/')).where((p) => !p.endsWith('.gitkeep'));
      expect(files, isNotEmpty);
      for (final f in files) {
        final c = byFile[f];
        expect(c, isNotNull, reason: '$f is missing from assets/credits.csv');
        expect(c!.sourceUrl, startsWith('https://'));
        expect(c.author, isNotEmpty);
        expect(c.licence, isNotEmpty);
      }
    });

    test('videos are short enough to bundle', () {
      for (final f in Directory('assets/video').listSync().whereType<File>()) {
        expect(f.lengthSync(), lessThan(3 * 1024 * 1024), reason: f.path);
      }
    });
  });

  group('cost breakdown', () {
    const totals = Totals(
      entries: 3000,
      transport: 0,
      meals: 22500,
      stay: 36000,
      hotel: 'mid',
      total: 61500,
      budget: 80000,
      left: 18500,
      perPerson: 15375,
    );

    test('parts are largest first and leave out zero amounts', () {
      final parts = costParts(totals);
      expect(parts.map((p) => p.label), ['Mid-range hotel', 'Food', 'Entry']);
      expect(parts.first.amount, 36000);
    });

    testWidgets('shows total, parts and what is left', (tester) async {
      googleFontsEnabled = false;
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: CostBreakdown(totals: totals))));
      expect(find.text('Rs 61,500'), findsOneWidget);
      expect(find.text('Mid-range hotel'), findsOneWidget);
      expect(find.text('Left over'), findsOneWidget);
      expect(find.text('Rs 18,500'), findsOneWidget);
    });
  });

  testWidgets('city carousel moves on by itself', (tester) async {
    setScreen(tester, 400, 800);
    googleFontsEnabled = false;
    const cities = [
      City(id: 'lahore', name: 'Lahore', province: 'Punjab', image: '', description: '', places: 28),
      City(id: 'karachi', name: 'Karachi', province: 'Sindh', image: '', description: '', places: 27),
    ];
    City? tapped;
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: CityCarousel(cities: cities, interval: const Duration(seconds: 2), onTap: (c) => tapped = c),
      ),
    ));
    final page = find.byType(PageView);
    double offset() => tester.widget<PageView>(page).controller!.offset;
    final start = offset();
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();
    expect(offset(), greaterThan(start));
    await tester.tap(find.text('Karachi').first);
    expect(tapped?.id, 'karachi');
  });

  testWidgets('Home lists recent trips when there are some', (tester) async {
    setScreen(tester, 400, 900);
    final trip = Map<String, dynamic>.from(samplePlan())..['image'] = '';
    final state = await signedIn(client: fakeBackend(recent: [trip]));
    await tester.pumpWidget(appWith(state, const AppShell()));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Recent trips'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('Balanced Explorer'), findsOneWidget);
  });

  testWidgets('chat shows the bot avatar, suggestion pills and a date pill when a date is needed', (tester) async {
    setScreen(tester, 400, 800);
    final state = await signedIn(client: fakeBackend(chatAwaiting: 'start_date'));
    await tester.pumpWidget(appWith(state, const ChatScreen()));
    await tester.pumpAndSettle();
    expect(find.byType(BotAvatar), findsOneWidget);
    expect(find.widgetWithText(SuggestionPill, 'Pick a date'), findsOneWidget);
    expect(find.widgetWithText(SuggestionPill, 'Lahore'), findsOneWidget);
    expect(find.byTooltip('Date'), findsOneWidget);
  });

  group('plan detail', () {
    Itinerary trip() {
      final j = Map<String, dynamic>.from(samplePlan())..['image'] = '';
      return Itinerary.fromJson(j);
    }

    Future<void> open(WidgetTester tester) async {
      final state = await signedIn();
      await state.setShow('map', false);
      await state.setShow('photos', false);
      await tester.pumpWidget(appWith(state, PlanDetailScreen(itinerary: trip())));
      await tester.pumpAndSettle();
    }

    testWidgets('shows a numbered timeline, the day selector and costs on a phone', (tester) async {
      setScreen(tester, 400, 900);
      await open(tester);
      expect(find.text('Day 1'), findsOneWidget);
      expect(find.text('Rs 74,100'), findsWidgets);
      await tester.scrollUntilVisible(find.text('Lahore Fort'), 300, scrollable: find.byType(Scrollable).first);
      expect(find.text('1'), findsOneWidget);
      expect(find.text('Lunch'), findsOneWidget);
    });

    testWidgets('puts the costs beside the timeline on wide screens', (tester) async {
      setScreen(tester, 1400, 1000);
      await open(tester);
      await tester.scrollUntilVisible(find.text('Lahore Fort'), 300, scrollable: find.byType(Scrollable).first);
      final fort = tester.getTopLeft(find.text('Lahore Fort'));
      final total = tester.getTopLeft(find.text('TOTAL'));
      expect(total.dx, greaterThan(fort.dx));
    });
  });
}
