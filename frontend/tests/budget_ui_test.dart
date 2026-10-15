import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:qissago/core/models.dart';
import 'package:qissago/core/trip_pdf.dart';
import 'package:qissago/screens/plan_detail_screen.dart';
import 'package:qissago/screens/quick_plan_screen.dart';
import 'package:qissago/widgets/cost_breakdown.dart';

import 'helpers.dart';
import 'models_test.dart' show samplePlan;

void main() {
  group('cost parts', () {
    test('road trip and jeep hire appear with their own labels', () {
      final t = Totals.fromJson({
        'entries': 3200,
        'transport': 1800,
        'jeep': 15000,
        'jeep_days': 1,
        'meals': 4200,
        'stay': 6000,
        'hotel': 'budget',
        'travel_to_city': 36000,
        'home_city': 'lahore',
        'travel_mode': 'bus',
        'traveller_type': 'foreign',
        'total': 66200,
        'budget': 100000,
        'left': 33800,
        'per_person': 33100,
      });
      expect(t.travellerType, 'foreign');
      final labels = costParts(t).map((p) => p.label).toList();
      expect(labels, ['Bus to the city', 'Jeep hire', 'Hotel', 'Food', 'Entry', 'Local transport']);
      expect(costParts(t).fold<int>(0, (s, p) => s + p.amount), t.total);
      expect(pdfCostParts(t).map((p) => p.$1), labels);
    });

    test('by car the road trip is fuel', () {
      final t = Totals.fromJson({'travel_to_city': 9000, 'travel_mode': 'car', 'total': 9000});
      expect(costParts(t).single.label, 'Fuel to the city');
    });

    test('older plans without the new fields still read', () {
      final t = Totals.fromJson({'entries': 100, 'total': 100});
      expect(t.jeep, 0);
      expect(t.travelToCity, 0);
      expect(t.travellerType, 'local');
    });
  });

  test('legs driven by the hired jeep are marked', () {
    expect(Leg.fromJson({'km': 4, 'minutes': 12, 'cost': 0, 'mode': 'jeep'}).byJeep, true);
    expect(Leg.fromJson({'km': 4, 'minutes': 12, 'cost': 600}).byJeep, false);
  });

  testWidgets('options form sends visitor type, home city and travel mode', (tester) async {
    setScreen(tester, 420, 2400);
    final sent = <Map<String, dynamic>>[];
    final state = await signedIn(client: fakeBackend(generated: sent));
    await tester.pumpWidget(appWith(state, const QuickPlanScreen()));
    await tester.pumpAndSettle();

    // City tiles show every destination with its photo.
    expect(find.byType(CityPicker), findsOneWidget);
    await tester.tap(find.descendant(of: find.byType(CityPicker), matching: find.text('Karachi')));
    await tester.pump();
    await tester.tap(find.widgetWithText(ChoiceChip, 'Foreign'));
    await tester.pump();
    // Karachi is the destination, so it is not offered as the starting city.
    expect(find.widgetWithText(ChoiceChip, 'Karachi'), findsNothing);
    await tester.tap(find.widgetWithText(ChoiceChip, 'Lahore'));
    await tester.pump();
    await tester.tap(find.widgetWithText(ChoiceChip, 'Own car'));
    await tester.pump();
    await tester.tap(find.text('Create plans'));
    await tester.pump(const Duration(seconds: 3));
    await tester.pumpAndSettle();

    final prefs = sent.single['preferences'] as Map<String, dynamic>;
    expect(prefs['city'], 'karachi');
    expect(prefs['traveller_type'], 'foreign');
    expect(prefs['home_city'], 'lahore');
    expect(prefs['travel_mode'], 'car');
  });

  testWidgets('a drive covered by the hired jeep shows Jeep instead of a fare', (tester) async {
    setScreen(tester, 400, 1200);
    final j = samplePlan()..['image'] = '';
    final items = (j['plan']['days'] as List).first['items'] as List;
    items.add({
      'kind': 'stop',
      'id': 'deosai',
      'name': 'Deosai National Park',
      'category': 'national park',
      'tags': ['nature'],
      'start': '14:00',
      'end': '17:00',
      'minutes': 180,
      'cost_group': 1000,
      'outdoor': true,
      'lat': 35.02,
      'lon': 75.41,
      'leg': {'km': 30.5, 'minutes': 90, 'cost': 0, 'mode': 'jeep'},
    });
    final state = await signedIn();
    await state.setShow('map', false);
    await state.setShow('photos', false);
    await tester.pumpWidget(appWith(state, PlanDetailScreen(itinerary: Itinerary.fromJson(j))));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.text('Deosai National Park'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.textContaining('Jeep'), findsOneWidget);
  });
}
