import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:qissago/core/models.dart';
import 'package:qissago/core/trip_pdf.dart';
import 'package:qissago/screens/plan_detail_screen.dart';
import 'package:qissago/widgets/cost_breakdown.dart';

import 'helpers.dart';
import 'models_test.dart' show samplePlan;

/// Two days, two photographed stops (one photo used twice), one break.
Itinerary twoDayTrip() {
  final j = jsonDecode(jsonEncode(samplePlan())) as Map<String, dynamic>;
  final day1 = (j['plan']['days'] as List).first as Map<String, dynamic>;
  final fort = (day1['items'] as List).first as Map<String, dynamic>;
  fort
    ..['image'] = '/static/images/pois/lhr_fort.jpg'
    ..['image_credit'] = 'Ali Khan'
    ..['image_license'] = 'CC BY-SA 4.0';
  final day2 = jsonDecode(jsonEncode(day1)) as Map<String, dynamic>
    ..['day'] = 2
    ..['date'] = '2026-10-17'
    ..['weekday'] = 'Sat';
  final mosque = jsonDecode(jsonEncode(fort)) as Map<String, dynamic>
    ..['id'] = 'lhr_badshahi'
    ..['name'] = 'Badshahi Mosque'
    ..['image'] = '/static/images/pois/lhr_badshahi.jpg'
    ..['image_credit'] = 'Sara Shah'
    ..['image_license'] = 'CC BY 2.0'
    ..['leg'] = {'km': 1.2, 'minutes': 6, 'cost': 70};
  (day2['items'] as List).add(mosque);
  (j['plan']['days'] as List).add(day2);
  j['days'] = 2;
  j['plan']['totals']['entries'] = 3000;
  j['plan']['totals']['transport'] = 600;
  return Itinerary.fromJson(j);
}

PdfAssets fontsOnly() {
  pw.Font font(String name) => pw.Font.ttf(File('assets/fonts/$name').readAsBytesSync().buffer.asByteData());
  return PdfAssets(
    display: font('DMSerifDisplay-Regular.ttf'),
    body: font('PlusJakartaSans-Regular.ttf'),
    bold: font('PlusJakartaSans-Bold.ttf'),
  );
}

int pageCount(List<int> bytes) => RegExp(r'/Type\s*/Page[^s]').allMatches(latin1.decode(bytes)).length;

void main() {
  test('photo credits list each photo once, in visiting order', () {
    final credits = tripPhotoCredits(twoDayTrip());
    expect(credits.map((c) => c.place), ['Lahore Fort', 'Badshahi Mosque']);
    expect(credits.first.author, 'Ali Khan');
    expect(credits.last.licence, 'CC BY 2.0');
  });

  test('file name has the city and start date', () {
    expect(tripPdfName(twoDayTrip()), 'qissago-lahore-2026-10-16.pdf');
  });

  test('PDF cost parts match the app, in the same colours', () {
    final t = twoDayTrip().totals;
    expect(pdfCostParts(t).map((p) => (p.$1, p.$2)), costParts(t).map((p) => (p.label, p.amount)));
    expect(pdfCostParts(t).map((p) => p.$3.toInt()), costParts(t).map((p) => p.color.toARGB32()));
  });

  test('builds a cover page plus the day pages, with the brand fonts embedded', () async {
    final bytes = await buildTripPdf(twoDayTrip(), fontsOnly(), compress: false);
    expect(latin1.decode(bytes.sublist(0, 5)), '%PDF-');
    expect(pageCount(bytes), greaterThanOrEqualTo(2));
    final text = latin1.decode(bytes);
    expect(text, contains('DMSerifDisplay'));
    expect(text, contains('PlusJakartaSans'));
    // No emoji-capable or fallback fonts are needed.
    expect(text, isNot(contains('Helvetica')));
  });

  test('a long trip flows onto more pages', () async {
    final trip = twoDayTrip();
    final j = jsonDecode(jsonEncode(samplePlan())) as Map<String, dynamic>;
    final day = (trip.plan['days'] as List).last;
    j['plan']['days'] = List.generate(7, (i) => {...(day as Map), 'day': i + 1});
    final long = Itinerary.fromJson(j);
    final short = await buildTripPdf(trip, fontsOnly(), compress: false);
    final longer = await buildTripPdf(long, fontsOnly(), compress: false);
    expect(pageCount(longer), greaterThan(pageCount(short)));
  });

  testWidgets('assets: fonts from the bundle, photos from the server, missing photos skipped', (tester) async {
    final jpg = File('assets/images/home_hero.jpg').readAsBytesSync();
    final requested = <String>[];
    final client = MockClient((req) async {
      requested.add(req.url.path);
      if (req.url.path.endsWith('lhr_fort.jpg')) return http.Response.bytes(jpg, 200);
      return http.Response('', 404);
    });
    final assets = await tester.runAsync(() => loadPdfAssets(twoDayTrip(), client: client));
    expect(assets!.cover, isNotNull);
    expect(assets.photos.keys, ['/static/images/pois/lhr_fort.jpg']);
    expect(requested.toSet(), {'/static/images/pois/lhr_fort.jpg', '/static/images/pois/lhr_badshahi.jpg'});
  });

  testWidgets('plan detail has a Download PDF button', (tester) async {
    setScreen(tester, 400, 900);
    final state = await signedIn();
    await state.setShow('map', false);
    await state.setShow('photos', false);
    final j = Map<String, dynamic>.from(samplePlan())..['image'] = '';
    await tester.pumpWidget(appWith(state, PlanDetailScreen(itinerary: Itinerary.fromJson(j))));
    await tester.pumpAndSettle();
    expect(find.widgetWithText(FilledButton, 'Download PDF'), findsOneWidget);
    expect(find.byTooltip('Download PDF'), findsOneWidget);
  });
}
