import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../theme.dart';
import '../widgets/nav.dart';
import 'credits_screen.dart';
import 'shell.dart';

/// Profile tab: name, email and log out.
class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();
    final user = state.user;
    final shell = ShellScope.maybeOf(context);
    // On phones Profile is reached from the avatar, so it behaves like an inner screen with a way back.
    final inner = shell != null && !isWide(context);
    return Scaffold(
      appBar: AppBar(
        title: Text('Profile', style: display(24)),
        automaticallyImplyLeading: false,
        leading: inner ? IconButton(onPressed: shell.leaveProfile, icon: const Icon(Icons.arrow_back)) : null,
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(24, 24, 24, 40),
            children: [
              Center(child: InitialAvatar(name: user?.name ?? '', size: 104)),
              const SizedBox(height: 20),
              Text(user?.name ?? '', textAlign: TextAlign.center, style: display(32)),
              const SizedBox(height: 6),
              Text(user?.email ?? '',
                  textAlign: TextAlign.center, style: const TextStyle(color: Palette.muted, fontSize: 15)),
              const SizedBox(height: 32),
              OutlinedButton.icon(
                onPressed: () => Navigator.of(context).push(MaterialPageRoute(builder: (_) => const CreditsScreen())),
                icon: const Icon(Icons.photo_library_outlined),
                label: const Text('Credits'),
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: () => context.read<AppState>().logout(),
                icon: const Icon(Icons.logout),
                label: const Text('Log out'),
              ),
              if (inner) BackHomeBar(onBack: shell.leaveProfile, padding: const EdgeInsets.only(top: 16)),
            ],
          ),
        ),
      ),
    );
  }
}
