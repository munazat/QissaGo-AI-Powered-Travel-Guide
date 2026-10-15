import 'package:intl/intl.dart';

final _money = NumberFormat.decimalPattern('en_US');

String rupees(int value) => 'Rs ${_money.format(value)}';

String shortDate(DateTime d) => DateFormat('d MMM').format(d);

String longDate(DateTime d) => DateFormat('EEE d MMM yyyy').format(d);

String dateRange(DateTime start, int days) {
  final end = start.add(Duration(days: days - 1));
  if (days <= 1) return DateFormat('EEE d MMM').format(start);
  if (start.month == end.month) return '${start.day}–${DateFormat('d MMM').format(end)}';
  return '${shortDate(start)} – ${shortDate(end)}';
}

String duration(int minutes) {
  if (minutes < 60) return '$minutes min';
  final h = minutes ~/ 60;
  final m = minutes % 60;
  return m == 0 ? '$h h' : '$h h $m min';
}

String isoDate(DateTime d) => DateFormat('yyyy-MM-dd').format(d);

String titleCase(String s) => s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);
