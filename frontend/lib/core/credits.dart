/// Reads assets/credits.csv: where each bundled photo and video came from.
class Credit {
  final String file;
  final String title;
  final String sourceUrl;
  final String author;
  final String licence;
  final String licenceUrl;
  final bool attributionRequired;

  const Credit({
    required this.file,
    required this.title,
    required this.sourceUrl,
    required this.author,
    required this.licence,
    required this.licenceUrl,
    required this.attributionRequired,
  });

  bool get isVideo => file.endsWith('.mp4');
}

/// Minimal CSV parser: commas, double-quoted fields, "" inside quotes, \n or \r\n line ends.
List<List<String>> parseCsv(String text) {
  final rows = <List<String>>[];
  var row = <String>[];
  final field = StringBuffer();
  var quoted = false;
  for (var i = 0; i < text.length; i++) {
    final ch = text[i];
    if (quoted) {
      if (ch == '"') {
        if (i + 1 < text.length && text[i + 1] == '"') {
          field.write('"');
          i++;
        } else {
          quoted = false;
        }
      } else {
        field.write(ch);
      }
    } else if (ch == '"') {
      quoted = true;
    } else if (ch == ',') {
      row.add(field.toString());
      field.clear();
    } else if (ch == '\n' || ch == '\r') {
      if (ch == '\r' && i + 1 < text.length && text[i + 1] == '\n') i++;
      row.add(field.toString());
      field.clear();
      if (row.any((f) => f.isNotEmpty)) rows.add(row);
      row = <String>[];
    } else {
      field.write(ch);
    }
  }
  row.add(field.toString());
  if (row.any((f) => f.isNotEmpty)) rows.add(row);
  return rows;
}

List<Credit> parseCredits(String text) {
  final rows = parseCsv(text);
  if (rows.isEmpty) return [];
  final head = rows.first;
  String col(List<String> r, String name) {
    final i = head.indexOf(name);
    return i >= 0 && i < r.length ? r[i] : '';
  }

  return [
    for (final r in rows.skip(1))
      Credit(
        file: col(r, 'file'),
        title: col(r, 'title'),
        sourceUrl: col(r, 'source_url'),
        author: col(r, 'author'),
        licence: col(r, 'licence'),
        licenceUrl: col(r, 'licence_url'),
        attributionRequired: col(r, 'attribution_required') == 'yes',
      ),
  ];
}
