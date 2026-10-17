import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:qissago/theme.dart';
import 'package:qissago/widgets/common.dart';

Widget wrap(Widget child) => MaterialApp(theme: buildTheme(useGoogleFonts: false), home: Scaffold(body: child));

void main() {
  testWidgets('score ring shows the score', (tester) async {
    await tester.pumpWidget(wrap(const ScoreRing(score: 87)));
    expect(find.text('87'), findsOneWidget);
  });

  testWidgets('pill shows text and icon', (tester) async {
    await tester.pumpWidget(wrap(const Pill('Rs 1,500', icon: Icons.payments_outlined)));
    expect(find.text('Rs 1,500'), findsOneWidget);
    expect(find.byIcon(Icons.payments_outlined), findsOneWidget);
  });

  testWidgets('image without a photo shows the placeholder', (tester) async {
    await tester.pumpWidget(wrap(const SizedBox(width: 100, height: 100, child: NetImage(path: ''))));
    expect(find.byIcon(Icons.landscape_outlined), findsOneWidget);
  });

  testWidgets('error view retries', (tester) async {
    var tapped = false;
    await tester.pumpWidget(wrap(ErrorRetry(message: 'Cannot reach the server', onRetry: () => tapped = true)));
    await tester.tap(find.text('Retry'));
    expect(tapped, true);
  });
}
