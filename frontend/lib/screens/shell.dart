import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../theme.dart';
import '../widgets/nav.dart';
import 'home_screen.dart';
import 'plan_hub_screen.dart';
import 'profile_screen.dart';
import 'saved_screen.dart';
import 'soon_screen.dart';

/// Screens at least this wide get the top bar; narrower ones get the bottom bar.
const wideBreakpoint = 700.0;

bool isWide(BuildContext context) => MediaQuery.sizeOf(context).width >= wideBreakpoint;

enum AppTab {
  home('Home', 'Home', Icons.home_outlined, Icons.home),
  plan('Plan', 'Plan', Icons.explore_outlined, Icons.explore),
  saved('Saved', 'Saved', Icons.bookmark_border, Icons.bookmark),
  narration('Narration', 'Narration', Icons.graphic_eq, Icons.graphic_eq, soon: true),
  video('Video', 'Travel Video', Icons.movie_outlined, Icons.movie, soon: true),
  profile('Profile', 'Profile', Icons.person_outline, Icons.person);

  const AppTab(this.label, this.wideLabel, this.icon, this.selectedIcon, {this.soon = false});

  final String label;
  final String wideLabel;
  final IconData icon;
  final IconData selectedIcon;
  final bool soon;

  /// Tabs in the phone bottom bar. Profile opens from the avatar instead.
  static const bottom = [home, plan, saved, narration, video];
}

/// Which tab is open, the navigator of each tab, and what the Plan tab should show.
class ShellController extends ChangeNotifier {
  AppTab tab = AppTab.home;
  AppTab _beforeProfile = AppTab.home;
  final Map<AppTab, GlobalKey<NavigatorState>> keys = {for (final t in AppTab.values) t: GlobalKey<NavigatorState>()};

  /// 'chat' or 'options'.
  String planMode = 'chat';

  /// City picked on Home; a new value resets the options form.
  String? planCity;
  int planVersion = 0;

  NavigatorState? _nav(AppTab t) => keys[t]!.currentState;

  void select(AppTab t) {
    if (t == tab) {
      _nav(t)?.popUntil((r) => r.isFirst);
      return;
    }
    if (t == AppTab.profile) _beforeProfile = tab;
    tab = t;
    notifyListeners();
  }

  void goHome() {
    _nav(AppTab.home)?.popUntil((r) => r.isFirst);
    if (tab != AppTab.home) {
      tab = AppTab.home;
      notifyListeners();
    }
  }

  /// Leaves Profile and returns to the tab that was open before it.
  void leaveProfile() => select(_beforeProfile == AppTab.profile ? AppTab.home : _beforeProfile);

  void openPlan(String mode, {String? cityId}) {
    planMode = mode;
    if (cityId != null) {
      planCity = cityId;
      planVersion++;
    }
    _nav(AppTab.plan)?.popUntil((r) => r.isFirst);
    tab = AppTab.plan;
    notifyListeners();
  }

  void setPlanMode(String mode) {
    planMode = mode;
    notifyListeners();
  }

  /// System back: pop inside the tab first, then return to Home. False means leave the app.
  bool handleBack() {
    final nav = _nav(tab);
    if (nav != null && nav.canPop()) {
      nav.pop();
      return true;
    }
    if (tab == AppTab.profile) {
      leaveProfile();
      return true;
    }
    if (tab != AppTab.home) {
      tab = AppTab.home;
      notifyListeners();
      return true;
    }
    return false;
  }
}

/// Gives screens access to the [ShellController].
class ShellScope extends InheritedNotifier<ShellController> {
  const ShellScope({super.key, required ShellController controller, required super.child})
      : super(notifier: controller);

  static ShellController? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<ShellScope>()?.notifier;

  static ShellController of(BuildContext context) {
    final c = maybeOf(context);
    assert(c != null, 'No ShellScope above this widget');
    return c!;
  }
}

/// The logged-in app: one navigator per tab, with a top bar (wide) or bottom bar (phone).
class AppShell extends StatefulWidget {
  const AppShell({super.key, this.controller});

  final ShellController? controller;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  late final ShellController _shell = widget.controller ?? ShellController();
  final Set<AppTab> _opened = {};

  @override
  void dispose() {
    if (widget.controller == null) _shell.dispose();
    super.dispose();
  }

  Widget _root(AppTab t) {
    switch (t) {
      case AppTab.home:
        return const HomeScreen();
      case AppTab.plan:
        return const PlanHubScreen();
      case AppTab.saved:
        return const SavedScreen();
      case AppTab.narration:
        return const SoonScreen(tab: AppTab.narration);
      case AppTab.video:
        return const SoonScreen(tab: AppTab.video);
      case AppTab.profile:
        return const ProfileScreen();
    }
  }

  @override
  Widget build(BuildContext context) {
    return ShellScope(
      controller: _shell,
      child: ListenableBuilder(
        listenable: _shell,
        builder: (context, _) {
          final tab = _shell.tab;
          _opened.add(tab);
          // Tabs are built the first time they are opened, then kept alive.
          final body = Semantics(
            container: true,
            child: IndexedStack(
              index: tab.index,
              children: [
                for (final t in AppTab.values)
                  _opened.contains(t)
                      ? TickerMode(
                          enabled: t == tab,
                          child: HeroControllerScope(
                            controller: MaterialApp.createMaterialHeroController(),
                            child: Navigator(
                              key: _shell.keys[t],
                              onGenerateRoute: (_) => MaterialPageRoute(builder: (_) => _root(t)),
                            ),
                          ),
                        )
                      : const SizedBox.shrink(),
              ],
            ),
          );
          return PopScope(
            canPop: false,
            onPopInvokedWithResult: (didPop, _) {
              if (didPop) return;
              if (!_shell.handleBack()) SystemNavigator.pop();
            },
            child: isWide(context)
                ? Scaffold(
                    // In the app bar slot the bar is painted after the tab, so the tab's page route
                    // cannot hide it from screen readers.
                    appBar: PreferredSize(
                      preferredSize: const Size.fromHeight(TopNavBar.height),
                      child: TopNavBar(
                        selected: tab,
                        userName: context.watch<AppState>().user?.name ?? '',
                        onSelect: _shell.select,
                      ),
                    ),
                    body: body,
                  )
                : Scaffold(
                    body: body,
                    bottomNavigationBar: BottomNavBar(selected: tab, onSelect: _shell.select),
                  ),
          );
        },
      ),
    );
  }
}

/// Avatar at the top right of each tab on phones. Wide screens use the Profile tab in the top bar instead.
class ProfileAvatar extends StatelessWidget {
  const ProfileAvatar({super.key, this.light = false});

  final bool light;

  @override
  Widget build(BuildContext context) {
    final shell = ShellScope.maybeOf(context);
    if (shell == null || isWide(context)) return const SizedBox.shrink();
    final name = context.watch<AppState>().user?.name ?? '';
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8),
      child: IconButton(
        tooltip: 'Profile',
        onPressed: () => shell.select(AppTab.profile),
        icon: InitialAvatar(name: name, size: 36, light: light),
      ),
    );
  }
}

/// Circle with the first letter of the user's name.
class InitialAvatar extends StatelessWidget {
  const InitialAvatar({super.key, required this.name, this.size = 36, this.light = false});

  final String name;
  final double size;
  final bool light;

  @override
  Widget build(BuildContext context) {
    final letter = name.trim().isEmpty ? '' : name.trim().characters.first.toUpperCase();
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: light ? Palette.paper : Palette.primary,
        border: Border.all(color: light ? Palette.primary : Palette.paper, width: 2),
      ),
      child: letter.isEmpty
          ? Icon(Icons.person, size: size * 0.55, color: Palette.onPrimary)
          : Text(letter,
              style: TextStyle(fontSize: size * 0.42, fontWeight: FontWeight.w800, color: Palette.onPrimary)),
    );
  }
}
