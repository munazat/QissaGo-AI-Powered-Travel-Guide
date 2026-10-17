import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:qissago/core/models.dart';
import 'package:qissago/screens/plans_screen.dart';
import 'package:qissago/screens/shell.dart';
import 'package:qissago/widgets/nav.dart';

import 'helpers.dart';

void main() {
  group('phone width', () {
    testWidgets('bottom bar has five tabs, Soon on Narration and Video, no Profile', (tester) async {
      setScreen(tester, 400, 800);
      final state = await signedIn();
      await tester.pumpWidget(appWith(state, const AppShell()));
      await tester.pumpAndSettle();

      expect(find.byType(BottomNavBar), findsOneWidget);
      expect(find.byType(TopNavBar), findsNothing);
      for (final label in ['Home', 'Plan', 'Saved', 'Narration', 'Video']) {
        expect(find.descendant(of: find.byType(BottomNavBar), matching: find.text(label)), findsOneWidget);
      }
      expect(find.descendant(of: find.byType(BottomNavBar), matching: find.text('Profile')), findsNothing);
      expect(find.descendant(of: find.byType(BottomNavBar), matching: find.byType(SoonBadge)), findsNWidgets(2));
    });

    testWidgets('Narration tab shows the placeholder and Home returns', (tester) async {
      setScreen(tester, 400, 800);
      final state = await signedIn();
      final shell = ShellController();
      await tester.pumpWidget(appWith(state, AppShell(controller: shell)));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Narration'));
      await tester.pumpAndSettle();
      expect(shell.tab, AppTab.narration);
      expect(find.text('Narration'), findsWidgets);

      await tester.tap(find.widgetWithText(FilledButton, 'Home'));
      await tester.pumpAndSettle();
      expect(shell.tab, AppTab.home);
    });

    testWidgets('avatar opens Profile with name, email, back and log out', (tester) async {
      setScreen(tester, 400, 800);
      final state = await signedIn();
      final shell = ShellController();
      await tester.pumpWidget(appWith(state, AppShell(controller: shell)));
      await tester.pumpAndSettle();

      await tester.tap(find.byTooltip('Profile').first);
      await tester.pumpAndSettle();
      expect(shell.tab, AppTab.profile);
      expect(find.text('Ayesha Khan'), findsOneWidget);
      expect(find.text('ayesha@example.com'), findsOneWidget);

      await tester.tap(find.widgetWithText(OutlinedButton, 'Back'));
      await tester.pumpAndSettle();
      expect(shell.tab, AppTab.home);

      await tester.tap(find.byTooltip('Profile').first);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Log out'));
      await tester.pumpAndSettle();
      expect(state.loggedIn, false);
    });

    testWidgets('Chat button on Home opens the Plan tab in chat mode', (tester) async {
      setScreen(tester, 400, 800);
      final state = await signedIn();
      final shell = ShellController();
      await tester.pumpWidget(appWith(state, AppShell(controller: shell)));
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Options'));
      await tester.pumpAndSettle();
      expect(shell.tab, AppTab.plan);
      expect(shell.planMode, 'options');

      shell.select(AppTab.home);
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Chat'));
      await tester.pumpAndSettle();
      expect(shell.planMode, 'chat');
      expect(find.text('Where would you like to go?'), findsOneWidget);
    });
  });

  testWidgets('Saved tab shows an empty state and reloads after a save', (tester) async {
    setScreen(tester, 400, 800);
    final state = await signedIn();
    final shell = ShellController();
    await tester.pumpWidget(appWith(state, AppShell(controller: shell)));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Saved'));
    await tester.pumpAndSettle();
    expect(find.text('No saved trips'), findsWidgets);

    final before = state.savedVersion;
    state.savedChanged();
    expect(state.savedVersion, before + 1);
  });

  testWidgets('wide screens show all six tabs in the top bar', (tester) async {
    setScreen(tester, 1280, 800);
    final state = await signedIn();
    await tester.pumpWidget(appWith(state, const AppShell()));
    await tester.pumpAndSettle();

    expect(find.byType(TopNavBar), findsOneWidget);
    expect(find.byType(BottomNavBar), findsNothing);
    for (final label in ['Home', 'Plan', 'Saved', 'Narration', 'Travel Video', 'Profile']) {
      expect(find.descendant(of: find.byType(TopNavBar), matching: find.text(label)), findsOneWidget);
    }
    expect(find.descendant(of: find.byType(TopNavBar), matching: find.byType(SoonBadge)), findsNWidgets(2));
    // Screen readers can reach every tab in the bar.
    final semantics = tester.ensureSemantics();
    for (final label in ['Home', 'Plan', 'Saved', 'Narration, Soon', 'Travel Video, Soon', 'Profile']) {
      expect(find.bySemanticsLabel(label), findsOneWidget, reason: label);
    }
    semantics.dispose();
    // No avatar in the content on wide screens; Profile lives in the bar.
    expect(find.byTooltip('Profile'), findsNothing);
  });

  group('controller', () {
    test('back pops inside the tab, then returns Home, then lets the app close', () {
      final shell = ShellController();
      shell.select(AppTab.saved);
      expect(shell.handleBack(), true);
      expect(shell.tab, AppTab.home);
      expect(shell.handleBack(), false);
    });

    test('leaving Profile returns to the tab opened before it', () {
      final shell = ShellController();
      shell.select(AppTab.saved);
      shell.select(AppTab.profile);
      shell.leaveProfile();
      expect(shell.tab, AppTab.saved);
    });

    test('a city from Home resets the options form', () {
      final shell = ShellController();
      shell.openPlan('options', cityId: 'lahore');
      expect(shell.planCity, 'lahore');
      expect(shell.planVersion, 1);
      expect(shell.tab, AppTab.plan);
    });
  });

  testWidgets('plans screen offers Back to chat and Home', (tester) async {
    setScreen(tester, 400, 800);
    final state = await signedIn();
    final shell = ShellController();
    await tester.pumpWidget(appWith(state, AppShell(controller: shell)));
    await tester.pumpAndSettle();
    shell.select(AppTab.saved);
    await tester.pumpAndSettle();
    shell.keys[AppTab.saved]!.currentState!.push(MaterialPageRoute(
      builder: (_) => PlansScreen(plans: <Itinerary>[], source: 'chat'),
    ));
    await tester.pumpAndSettle();

    expect(find.text('Back to chat'), findsOneWidget);
    await tester.tap(find.text('Back to chat'));
    await tester.pumpAndSettle();
    expect(shell.tab, AppTab.plan);
    expect(shell.planMode, 'chat');

    shell.select(AppTab.saved);
    await tester.pumpAndSettle();
    expect(shell.keys[AppTab.saved]!.currentState!.canPop(), true);
    await tester.tap(find.widgetWithText(OutlinedButton, 'Home'));
    await tester.pumpAndSettle();
    expect(shell.tab, AppTab.home);
  });
}
