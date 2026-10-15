import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/app_state.dart';
import 'screens/auth_screen.dart';
import 'screens/shell.dart';
import 'theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    ChangeNotifierProvider(
      create: (_) => AppState()..init(),
      child: const QissaGoApp(),
    ),
  );
}

class QissaGoApp extends StatelessWidget {
  const QissaGoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'QissaGo',
      debugShowCheckedModeBanner: false,
      theme: buildTheme(),
      home: const RootGate(),
    );
  }
}

/// Shows the login screen or the home screen, depending on whether someone is logged in.
class RootGate extends StatelessWidget {
  const RootGate({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    if (state.loading) {
      return const Scaffold(
        body: DecoratedBox(
          decoration: BoxDecoration(gradient: Palette.heroGradient),
          child: Center(child: CircularProgressIndicator(color: Colors.white)),
        ),
      );
    }
    return state.loggedIn ? const AppShell() : const AuthScreen();
  }
}
