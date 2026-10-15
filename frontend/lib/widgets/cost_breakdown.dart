import 'package:flutter/material.dart';

import '../core/format.dart';
import '../core/models.dart';
import '../theme.dart';

class CostPart {
  final String label;
  final int amount;
  final Color color;

  const CostPart(this.label, this.amount, this.color);
}

/// The parts of a trip's cost, largest first, leaving out anything that costs nothing.
List<CostPart> costParts(Totals t) {
  final parts = [
    CostPart(t.hotel == 'mid' ? 'Mid-range hotel' : 'Hotel', t.stay, Palette.slate),
    CostPart(t.travelMode == 'car' ? 'Fuel to the city' : 'Bus to the city', t.travelToCity, Palette.primaryDeep),
    CostPart('Food', t.meals, Palette.primary),
    CostPart('Entry', t.entries, Palette.terracotta),
    CostPart('Local transport', t.transport, Palette.terracottaDeep),
    CostPart('Jeep hire', t.jeep, Palette.stone),
  ].where((p) => p.amount > 0).toList()
    ..sort((a, b) => b.amount.compareTo(a.amount));
  return parts;
}

/// Total, a stacked bar of where the money goes, and a legend.
class CostBreakdown extends StatelessWidget {
  const CostBreakdown({super.key, required this.totals});

  final Totals totals;

  @override
  Widget build(BuildContext context) {
    final t = totals;
    final parts = costParts(t);
    final sum = parts.fold<int>(0, (a, p) => a + p.amount);
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(color: Palette.paper, borderRadius: BorderRadius.circular(28)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('TOTAL', style: labelStyle),
                    const SizedBox(height: 4),
                    Text(rupees(t.total), style: display(34)),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  const Text('PER PERSON', style: labelStyle),
                  const SizedBox(height: 4),
                  Text(rupees(t.perPerson), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (sum > 0)
            ClipRRect(
              borderRadius: BorderRadius.circular(8),
              child: SizedBox(
                height: 14,
                child: Row(
                  children: [
                    for (final p in parts)
                      Expanded(
                        flex: (p.amount * 1000 / sum).round().clamp(1, 1000),
                        child: Container(color: p.color),
                      ),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 14),
          for (final p in parts)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  Container(
                    width: 12,
                    height: 12,
                    decoration: BoxDecoration(color: p.color, borderRadius: BorderRadius.circular(4)),
                  ),
                  const SizedBox(width: 10),
                  Expanded(child: Text(p.label, style: const TextStyle(fontWeight: FontWeight.w600))),
                  Text(rupees(p.amount), style: const TextStyle(fontWeight: FontWeight.w700)),
                ],
              ),
            ),
          if (t.budget > 0) ...[
            const Divider(height: 24),
            Row(
              children: [
                const Expanded(child: Text('Budget', style: TextStyle(fontWeight: FontWeight.w600))),
                Text(rupees(t.budget), style: const TextStyle(fontWeight: FontWeight.w700)),
              ],
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                Expanded(
                  child: Text(t.left >= 0 ? 'Left over' : 'Over budget',
                      style: const TextStyle(fontWeight: FontWeight.w800)),
                ),
                Text(rupees(t.left.abs()), style: const TextStyle(fontWeight: FontWeight.w800)),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
