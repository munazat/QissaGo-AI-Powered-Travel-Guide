import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../core/format.dart';
import '../theme.dart';
import '../core/models.dart';
import '../widgets/common.dart';
import 'generating_screen.dart';

/// Plan with buttons instead of chat. Fills the same preferences the chatbot fills.
class QuickPlanScreen extends StatefulWidget {
  const QuickPlanScreen({super.key, this.cityId, this.embedded = false});

  final String? cityId;

  /// Inside the Plan tab, which has its own app bar.
  final bool embedded;

  @override
  State<QuickPlanScreen> createState() => _QuickPlanScreenState();
}

class _QuickPlanScreenState extends State<QuickPlanScreen> {
  String? _city;
  DateTime _start = DateTime.now().add(const Duration(days: 1));
  int _days = 2;
  String _group = 'couple';
  int _size = 2;
  double _budget = 50000;
  final Set<String> _interests = {};
  String _pace = 'balanced';
  final Set<String> _needs = {};
  String _traveller = 'local';
  String? _from;
  String _mode = 'bus';

  static const _groups = [('solo', 'Solo'), ('couple', 'Couple'), ('family', 'Family'), ('friends', 'Friends')];
  static const _paces = [('relaxed', 'Relaxed'), ('balanced', 'Balanced'), ('packed', 'Packed')];

  @override
  void initState() {
    super.initState();
    _city = widget.cityId;
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: _start,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: now.add(const Duration(days: 365)),
    );
    if (picked != null) setState(() => _start = picked);
  }

  void _setGroup(String g) {
    setState(() {
      _group = g;
      if (g == 'solo') _size = 1;
      if (g == 'couple') _size = 2;
      if ((g == 'family' || g == 'friends') && _size < 3) _size = 4;
    });
  }

  void _create() {
    if (_city == null) {
      showError(context, 'Choose a city');
      return;
    }
    final prefs = <String, dynamic>{
      'city': _city,
      'start_date': isoDate(_start),
      'days': _days,
      'budget': _budget.round(),
      'group_type': _group,
      'group_size': _size,
      'interests': _interests.toList(),
      'interests_answered': true,
      'pace': _pace,
      'needs': _needs.toList(),
      'traveller_type': _traveller,
      if (_from != null && _from != _city) 'home_city': _from,
      'travel_mode': _mode,
    };
    Navigator.of(context)
        .push(MaterialPageRoute(builder: (_) => GeneratingScreen(preferences: prefs, source: 'options')));
  }

  @override
  Widget build(BuildContext context) {
    final meta = context.watch<AppState>().meta;
    return Scaffold(
      appBar: widget.embedded ? null : AppBar(title: Text('Plan with options', style: display(24))),
      body: meta == null
          ? ErrorRetry(message: 'Cannot reach the server', onRetry: () => context.read<AppState>().loadMeta())
          : Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 760),
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 120),
                  children: [
                    const _Label('City'),
                    CityPicker(
                      cities: meta.cities,
                      selected: _city,
                      onSelect: (id) => setState(() {
                        _city = id;
                        if (_from == id) _from = null;
                      }),
                    ),
                    const _Label('Dates'),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: _pickDate,
                            icon: const Icon(Icons.event_outlined),
                            label: Text(longDate(_start)),
                          ),
                        ),
                        const SizedBox(width: 12),
                        _Stepper(
                          value: _days,
                          min: 1,
                          max: 7,
                          suffix: _days == 1 ? 'day' : 'days',
                          onChanged: (v) => setState(() => _days = v),
                        ),
                      ],
                    ),
                    const _Label('Travellers'),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final g in _groups)
                          ChoiceChip(label: Text(g.$2), selected: _group == g.$1, onSelected: (_) => _setGroup(g.$1)),
                      ],
                    ),
                    if (_group == 'family' || _group == 'friends') ...[
                      const SizedBox(height: 12),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: _Stepper(
                          value: _size,
                          min: 2,
                          max: 20,
                          suffix: 'people',
                          onChanged: (v) => setState(() => _size = v),
                        ),
                      ),
                    ],
                    const _Label('Visitor'),
                    Wrap(
                      spacing: 8,
                      children: [
                        for (final t in const [('local', 'Pakistani'), ('foreign', 'Foreign')])
                          ChoiceChip(
                            label: Text(t.$2),
                            selected: _traveller == t.$1,
                            onSelected: (_) => setState(() => _traveller = t.$1),
                          ),
                      ],
                    ),
                    const _Label('Travelling from'),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        ChoiceChip(
                          label: const Text('Already there'),
                          selected: _from == null,
                          onSelected: (_) => setState(() => _from = null),
                        ),
                        for (final c in meta.cities.where((c) => c.id != _city))
                          ChoiceChip(
                            label: Text(c.name),
                            selected: _from == c.id,
                            onSelected: (_) => setState(() => _from = c.id),
                          ),
                      ],
                    ),
                    if (_from != null) ...[
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 8,
                        children: [
                          for (final m in const [
                            ('bus', 'Bus', Icons.directions_bus_outlined),
                            ('car', 'Own car', Icons.directions_car_outlined)
                          ])
                            ChoiceChip(
                              avatar: Icon(m.$3, size: 18),
                              label: Text(m.$2),
                              selected: _mode == m.$1,
                              onSelected: (_) => setState(() => _mode = m.$1),
                            ),
                        ],
                      ),
                    ],
                    const _Label('Budget'),
                    Text(rupees(_budget.round()), style: display(30)),
                    Slider(
                      value: _budget,
                      min: 10000,
                      max: 500000,
                      divisions: 98,
                      label: rupees(_budget.round()),
                      onChanged: (v) => setState(() => _budget = v),
                    ),
                    const _Label('Interests'),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final i in meta.interests)
                          FilterChip(
                            label: Text(i.label),
                            selected: _interests.contains(i.id),
                            onSelected: (on) => setState(() => on ? _interests.add(i.id) : _interests.remove(i.id)),
                          ),
                      ],
                    ),
                    const _Label('Pace'),
                    Wrap(
                      spacing: 8,
                      children: [
                        for (final p in _paces)
                          ChoiceChip(
                            label: Text(p.$2),
                            selected: _pace == p.$1,
                            onSelected: (_) => setState(() => _pace = p.$1),
                          ),
                      ],
                    ),
                    const _Label('Needs'),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        for (final n in meta.needs)
                          FilterChip(
                            label: Text(n.label),
                            selected: _needs.contains(n.id),
                            onSelected: (on) => setState(() => on ? _needs.add(n.id) : _needs.remove(n.id)),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
      bottomNavigationBar: meta == null
          ? null
          : SafeArea(
              child: Center(
                heightFactor: 1,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 760),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(20, 8, 20, 16),
                    child: FilledButton.icon(
                      onPressed: _create,
                      icon: const Icon(Icons.auto_awesome),
                      label: const Text('Create plans'),
                    ),
                  ),
                ),
              ),
            ),
    );
  }
}

class _Label extends StatelessWidget {
  const _Label(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 24, bottom: 10),
      child: Text(text.toUpperCase(), style: labelStyle),
    );
  }
}

class _Stepper extends StatelessWidget {
  const _Stepper({
    required this.value,
    required this.min,
    required this.max,
    required this.suffix,
    required this.onChanged,
  });

  final int value;
  final int min;
  final int max;
  final String suffix;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Palette.paper,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Palette.line),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(onPressed: value > min ? () => onChanged(value - 1) : null, icon: const Icon(Icons.remove)),
          Text('$value $suffix', style: const TextStyle(fontWeight: FontWeight.w700)),
          IconButton(onPressed: value < max ? () => onChanged(value + 1) : null, icon: const Icon(Icons.add)),
        ],
      ),
    );
  }
}

/// Destinations as photo tiles in a horizontal row.
class CityPicker extends StatelessWidget {
  const CityPicker({super.key, required this.cities, required this.selected, required this.onSelect});

  final List<City> cities;
  final String? selected;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 150,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: cities.length,
        separatorBuilder: (_, __) => const SizedBox(width: 10),
        itemBuilder: (_, i) {
          final c = cities[i];
          final on = c.id == selected;
          return Semantics(
            selected: on,
            button: true,
            label: c.name,
            excludeSemantics: true,
            child: GestureDetector(
              onTap: () => onSelect(c.id),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 118,
                padding: EdgeInsets.all(on ? 3 : 0),
                decoration: BoxDecoration(
                  color: on ? Palette.primary : Colors.transparent,
                  borderRadius: BorderRadius.circular(22),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(on ? 19 : 22),
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      NetImage(path: c.image, label: c.name),
                      DecoratedBox(
                        decoration: BoxDecoration(gradient: Palette.photoShade(top: 0, bottom: 0.85, start: 0.45)),
                      ),
                      Positioned(
                        left: 10,
                        right: 8,
                        bottom: 10,
                        child: Text(c.name,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15)),
                      ),
                      if (on)
                        const Positioned(
                          top: 8,
                          right: 8,
                          child: CircleAvatar(
                            radius: 12,
                            backgroundColor: Palette.primary,
                            child: Icon(Icons.check, size: 16, color: Palette.onPrimary),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
