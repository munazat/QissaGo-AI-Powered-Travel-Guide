import 'package:flutter/material.dart';

import '../screens/shell.dart';
import '../theme.dart';

/// Small "Soon" tag for tabs that come in a later iteration.
class SoonBadge extends StatelessWidget {
  const SoonBadge({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(color: Palette.terracotta, borderRadius: BorderRadius.circular(8)),
      child: const Text('Soon',
          style: TextStyle(fontSize: 10, height: 1.2, fontWeight: FontWeight.w800, color: Palette.onPrimary)),
    );
  }
}

/// Top navigation for wide screens: logo on the left, all six tabs on the right.
class TopNavBar extends StatelessWidget {
  const TopNavBar({super.key, required this.selected, required this.userName, required this.onSelect});

  static const height = 68.0;

  final AppTab selected;
  final String userName;
  final ValueChanged<AppTab> onSelect;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Palette.slate,
      child: SafeArea(
        bottom: false,
        child: SizedBox(
          height: height,
          child: Row(
            children: [
              const SizedBox(width: 24),
              Text('QissaGo', style: display(26, color: Colors.white)),
              const SizedBox(width: 16),
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  reverse: true,
                  child: Row(
                    children: [
                      for (final t in AppTab.values)
                        _TopItem(
                          tab: t,
                          selected: t == selected,
                          userName: userName,
                          onTap: () => onSelect(t),
                        ),
                      const SizedBox(width: 16),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TopItem extends StatelessWidget {
  const _TopItem({required this.tab, required this.selected, required this.userName, required this.onTap});

  final AppTab tab;
  final bool selected;
  final String userName;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final fg = selected ? Palette.onPrimary : Colors.white;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 3),
      child: Semantics(
        selected: selected,
        button: true,
        label: tab.soon ? '${tab.wideLabel}, Soon' : tab.wideLabel,
        excludeSemantics: true,
        child: Material(
          color: selected ? Palette.primary : Colors.transparent,
          borderRadius: BorderRadius.circular(24),
          child: InkWell(
            borderRadius: BorderRadius.circular(24),
            onTap: onTap,
            child: Container(
              height: 44,
              padding: const EdgeInsets.symmetric(horizontal: 14),
              child: Row(
                children: [
                  if (tab == AppTab.profile)
                    InitialAvatar(name: userName, size: 26, light: !selected)
                  else
                    Icon(selected ? tab.selectedIcon : tab.icon, size: 20, color: fg),
                  const SizedBox(width: 8),
                  Text(tab.wideLabel, style: TextStyle(color: fg, fontWeight: FontWeight.w700, fontSize: 14)),
                  if (tab.soon) ...[const SizedBox(width: 6), const SoonBadge()],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Bottom navigation for phones. Profile is not here; it opens from the avatar.
class BottomNavBar extends StatelessWidget {
  const BottomNavBar({super.key, required this.selected, required this.onSelect});

  final AppTab selected;
  final ValueChanged<AppTab> onSelect;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Palette.paper,
      elevation: 10,
      shadowColor: Palette.slate.withValues(alpha: 0.3),
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 68,
          child: Row(
            children: [
              for (final t in AppTab.bottom)
                Expanded(child: _BottomItem(tab: t, selected: t == selected, onTap: () => onSelect(t))),
            ],
          ),
        ),
      ),
    );
  }
}

class _BottomItem extends StatelessWidget {
  const _BottomItem({required this.tab, required this.selected, required this.onTap});

  final AppTab tab;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: selected,
      button: true,
      label: tab.label,
      excludeSemantics: true,
      child: InkWell(
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Stack(
              clipBehavior: Clip.none,
              children: [
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 56,
                  height: 30,
                  decoration: BoxDecoration(
                    color: selected ? Palette.primary : Colors.transparent,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Icon(selected ? tab.selectedIcon : tab.icon,
                      size: 22, color: selected ? Palette.onPrimary : Palette.muted),
                ),
                if (tab.soon) const Positioned(right: -4, top: -9, child: SoonBadge()),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              tab.label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 12,
                fontWeight: selected ? FontWeight.w800 : FontWeight.w600,
                color: selected ? Palette.slate : Palette.muted,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Visible Back and Home buttons inside a screen's content, so nobody has to find the small arrow.
class BackHomeBar extends StatelessWidget {
  const BackHomeBar({
    super.key,
    this.backLabel = 'Back',
    this.onBack,
    this.padding = const EdgeInsets.fromLTRB(16, 12, 16, 4),
  });

  final String backLabel;

  /// Defaults to closing the current screen.
  final VoidCallback? onBack;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    final shell = ShellScope.maybeOf(context);
    return Padding(
      padding: padding,
      child: Wrap(
        spacing: 10,
        runSpacing: 8,
        children: [
          OutlinedButton.icon(
            onPressed: onBack ?? () => Navigator.of(context).maybePop(),
            icon: const Icon(Icons.arrow_back),
            label: Text(backLabel),
          ),
          if (shell != null)
            OutlinedButton.icon(
              onPressed: shell.goHome,
              icon: const Icon(Icons.home_outlined),
              label: const Text('Home'),
            ),
        ],
      ),
    );
  }
}
