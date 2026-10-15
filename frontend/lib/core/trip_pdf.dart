import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

import 'config.dart';
import 'format.dart';
import 'models.dart';

/// Brand colours for print (same values as Palette).
class PdfPalette {
  static const primary = PdfColor.fromInt(0xFF8FBC8F);
  static const primaryDeep = PdfColor.fromInt(0xFF3E6B4E);
  static const slate = PdfColor.fromInt(0xFF2F4F4F);
  static const onPrimary = PdfColor.fromInt(0xFF1F3636);
  static const sand = PdfColor.fromInt(0xFFE8E4D8);
  static const sage = PdfColor.fromInt(0xFFC7D3C0);
  static const terracotta = PdfColor.fromInt(0xFFD9A38F);
  static const terracottaDeep = PdfColor.fromInt(0xFFA86F5C);
  static const muted = PdfColor.fromInt(0xFF435A56);
  static const stone = PdfColor.fromInt(0xFFB7C2AF);
  static const paper = PdfColor.fromInt(0xFFF4F1EA);
}

/// Fonts and photos the PDF needs. Photos are optional; a missing one is simply left out.
class PdfAssets {
  final pw.Font display;
  final pw.Font body;
  final pw.Font bold;
  final pw.ImageProvider? cover;
  final Map<String, pw.ImageProvider> photos;

  const PdfAssets({required this.display, required this.body, required this.bold, this.cover, this.photos = const {}});
}

class PhotoCredit {
  final String place;
  final String author;
  final String licence;

  const PhotoCredit(this.place, this.author, this.licence);
}

/// One line per distinct photo used in the trip, in visiting order.
List<PhotoCredit> tripPhotoCredits(Itinerary trip) {
  final seen = <String>{};
  final out = <PhotoCredit>[];
  for (final day in trip.dayPlans) {
    for (final s in day.stops) {
      if (s.image.isEmpty || s.imageCredit.isEmpty || !seen.add(s.image)) continue;
      out.add(PhotoCredit(s.name, s.imageCredit, s.imageLicense));
    }
  }
  return out;
}

/// "qissago-lahore-2026-10-25.pdf"
String tripPdfName(Itinerary trip) {
  final city = trip.cityName.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '-');
  return 'qissago-$city-${isoDate(trip.startDate)}.pdf';
}

/// Loads fonts from the app bundle and downloads the cover and stop photos from the backend.
Future<PdfAssets> loadPdfAssets(Itinerary trip, {AssetBundle? bundle, http.Client? client}) async {
  final b = bundle ?? rootBundle;
  final c = client ?? http.Client();
  Future<pw.ImageProvider?> fetch(String path) async {
    final url = AppConfig.media(path);
    if (url.isEmpty) return null;
    try {
      final r = await c.get(Uri.parse(url)).timeout(const Duration(seconds: 20));
      if (r.statusCode != 200 || r.bodyBytes.isEmpty) return null;
      return pw.MemoryImage(r.bodyBytes);
    } catch (_) {
      return null;
    }
  }

  final stops = {
    for (final d in trip.dayPlans)
      for (final s in d.stops) s.image
  }..remove('');
  final results = await Future.wait([fetch(trip.image), for (final p in stops) fetch(p)]);
  final photos = <String, pw.ImageProvider>{};
  var i = 1;
  for (final p in stops) {
    final img = results[i++];
    if (img != null) photos[p] = img;
  }
  return PdfAssets(
    display: pw.Font.ttf(await b.load('assets/fonts/DMSerifDisplay-Regular.ttf')),
    body: pw.Font.ttf(await b.load('assets/fonts/PlusJakartaSans-Regular.ttf')),
    bold: pw.Font.ttf(await b.load('assets/fonts/PlusJakartaSans-Bold.ttf')),
    cover: results.first,
    photos: photos,
  );
}

/// The whole trip as a printable A4 document: cover, one section per day, photo credits.
Future<Uint8List> buildTripPdf(Itinerary trip, PdfAssets a, {bool compress = true}) {
  final doc = pw.Document(
    compress: compress,
    title: '${trip.title} - ${trip.cityName}',
    author: 'QissaGo',
    theme: pw.ThemeData.withFont(base: a.body, bold: a.bold),
  );
  final t = trip.totals;
  pw.TextStyle display(double size, [PdfColor color = PdfPalette.slate]) =>
      pw.TextStyle(font: a.display, fontSize: size, color: color);
  const label = pw.TextStyle(fontSize: 8, letterSpacing: 1.2, color: PdfPalette.muted);
  final people = '${trip.people} ${trip.people == 1 ? 'traveller' : 'travellers'}'
      '${trip.totals.travellerType == 'foreign' ? ', foreign' : ''}';

  pw.Widget footer(pw.Context ctx) => pw.Container(
        alignment: pw.Alignment.centerRight,
        margin: const pw.EdgeInsets.only(top: 12),
        child: pw.Text('QissaGo  ·  ${trip.title}  ·  ${ctx.pageNumber} / ${ctx.pagesCount}',
            style: const pw.TextStyle(fontSize: 8, color: PdfPalette.muted)),
      );

  // ------------------------------------------------------------------ cover
  doc.addPage(
    pw.Page(
      pageFormat: PdfPageFormat.a4,
      margin: pw.EdgeInsets.zero,
      build: (ctx) => pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.stretch,
        children: [
          pw.SizedBox(
            height: 430,
            child: pw.Stack(
              fit: pw.StackFit.expand,
              children: [
                if (a.cover != null) pw.Image(a.cover!, fit: pw.BoxFit.cover) else pw.Container(color: PdfPalette.sage),
                pw.Positioned(
                  left: 0,
                  right: 0,
                  bottom: 0,
                  child: pw.Container(
                    color: PdfPalette.slate,
                    padding: const pw.EdgeInsets.fromLTRB(36, 22, 36, 26),
                    child: pw.Column(
                      crossAxisAlignment: pw.CrossAxisAlignment.start,
                      children: [
                        pw.Text('QISSAGO',
                            style: const pw.TextStyle(fontSize: 9, letterSpacing: 2, color: PdfPalette.sage)),
                        pw.SizedBox(height: 6),
                        pw.Text(trip.title, style: display(34, PdfColors.white)),
                        pw.SizedBox(height: 6),
                        pw.Text('${trip.cityName}  ·  ${dateRange(trip.startDate, trip.days)} ${trip.startDate.year}',
                            style: const pw.TextStyle(fontSize: 12, color: PdfColors.white)),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          pw.Padding(
            padding: const pw.EdgeInsets.fromLTRB(36, 26, 36, 0),
            child: pw.Column(
              crossAxisAlignment: pw.CrossAxisAlignment.stretch,
              children: [
                pw.Row(
                  children: [
                    _stat('CITY', trip.cityName, a),
                    _stat(
                        'DATES',
                        '${dateRange(trip.startDate, trip.days)}  (${trip.days} ${trip.days == 1 ? 'day' : 'days'})',
                        a),
                    _stat('TRAVELLERS', people, a),
                    pw.Container(
                      width: 64,
                      height: 64,
                      alignment: pw.Alignment.center,
                      decoration: const pw.BoxDecoration(color: PdfPalette.terracotta, shape: pw.BoxShape.circle),
                      child: pw.Column(
                        mainAxisAlignment: pw.MainAxisAlignment.center,
                        children: [
                          pw.Text('${trip.matchScore}', style: display(22, PdfPalette.onPrimary)),
                          pw.Text('MATCH',
                              style: const pw.TextStyle(fontSize: 6, letterSpacing: 1, color: PdfPalette.onPrimary)),
                        ],
                      ),
                    ),
                  ],
                ),
                pw.SizedBox(height: 22),
                _costBlock(t, a, label),
              ],
            ),
          ),
        ],
      ),
    ),
  );

  // ------------------------------------------------------------------ days
  final credits = tripPhotoCredits(trip);
  doc.addPage(
    pw.MultiPage(
      pageFormat: PdfPageFormat.a4,
      margin: const pw.EdgeInsets.fromLTRB(36, 36, 36, 28),
      footer: footer,
      build: (ctx) => [
        for (final day in trip.dayPlans) ...[
          _dayHeader(day, display),
          pw.SizedBox(height: 10),
          _dayTable(day, a),
          pw.SizedBox(height: 26),
        ],
        if (credits.isNotEmpty) ...[
          pw.Text('Photo credits', style: display(18)),
          pw.SizedBox(height: 8),
          for (final c in credits)
            pw.Padding(
              padding: const pw.EdgeInsets.only(bottom: 3),
              child: pw.Text(
                '${c.place}: ${c.author}${c.licence.isEmpty ? '' : ', ${c.licence}'}, via Wikimedia Commons',
                style: const pw.TextStyle(fontSize: 8.5, color: PdfPalette.muted),
              ),
            ),
        ],
      ],
    ),
  );
  return doc.save();
}

pw.Widget _stat(String label, String value, PdfAssets a) => pw.Expanded(
      child: pw.Column(
        crossAxisAlignment: pw.CrossAxisAlignment.start,
        children: [
          pw.Text(label, style: const pw.TextStyle(fontSize: 8, letterSpacing: 1.2, color: PdfPalette.muted)),
          pw.SizedBox(height: 4),
          pw.Text(value, style: pw.TextStyle(font: a.bold, fontSize: 12, color: PdfPalette.slate)),
        ],
      ),
    );

/// Same parts and colours as the app's cost bar.
List<(String, int, PdfColor)> pdfCostParts(Totals t) {
  final parts = [
    (t.hotel == 'mid' ? 'Mid-range hotel' : 'Hotel', t.stay, PdfPalette.slate),
    (t.travelMode == 'car' ? 'Fuel to the city' : 'Bus to the city', t.travelToCity, PdfPalette.primaryDeep),
    ('Food', t.meals, PdfPalette.primary),
    ('Entry', t.entries, PdfPalette.terracotta),
    ('Local transport', t.transport, PdfPalette.terracottaDeep),
    ('Jeep hire', t.jeep, PdfPalette.stone),
  ].where((p) => p.$2 > 0).toList()
    ..sort((x, y) => y.$2.compareTo(x.$2));
  return parts;
}

pw.Widget _costBlock(Totals t, PdfAssets a, pw.TextStyle label) {
  final parts = pdfCostParts(t);
  final sum = parts.fold<int>(0, (s, p) => s + p.$2);
  pw.Widget row(String l, String v, {bool strong = false}) => pw.Padding(
        padding: const pw.EdgeInsets.symmetric(vertical: 3),
        child: pw.Row(children: [
          pw.Expanded(child: pw.Text(l, style: pw.TextStyle(font: strong ? a.bold : a.body, fontSize: 10.5))),
          pw.Text(v, style: pw.TextStyle(font: a.bold, fontSize: 10.5)),
        ]),
      );
  return pw.Container(
    padding: const pw.EdgeInsets.all(18),
    decoration: pw.BoxDecoration(color: PdfPalette.paper, borderRadius: pw.BorderRadius.circular(14)),
    child: pw.Column(
      crossAxisAlignment: pw.CrossAxisAlignment.stretch,
      children: [
        pw.Row(
          crossAxisAlignment: pw.CrossAxisAlignment.end,
          children: [
            pw.Expanded(
              child: pw.Column(crossAxisAlignment: pw.CrossAxisAlignment.start, children: [
                pw.Text('TOTAL COST', style: label),
                pw.SizedBox(height: 3),
                pw.Text(rupees(t.total), style: pw.TextStyle(font: a.display, fontSize: 28, color: PdfPalette.slate)),
              ]),
            ),
            pw.Column(crossAxisAlignment: pw.CrossAxisAlignment.end, children: [
              pw.Text('PER PERSON', style: label),
              pw.SizedBox(height: 3),
              pw.Text(rupees(t.perPerson), style: pw.TextStyle(font: a.bold, fontSize: 13)),
            ]),
          ],
        ),
        pw.SizedBox(height: 12),
        if (sum > 0)
          pw.ClipRRect(
            horizontalRadius: 4,
            verticalRadius: 4,
            child: pw.SizedBox(
              height: 10,
              child: pw.Row(children: [
                for (final p in parts)
                  pw.Expanded(flex: (p.$2 * 1000 / sum).round().clamp(1, 1000), child: pw.Container(color: p.$3)),
              ]),
            ),
          ),
        pw.SizedBox(height: 10),
        for (final p in parts)
          pw.Padding(
            padding: const pw.EdgeInsets.symmetric(vertical: 2.5),
            child: pw.Row(children: [
              pw.Container(width: 9, height: 9, color: p.$3),
              pw.SizedBox(width: 8),
              pw.Expanded(child: pw.Text(p.$1, style: const pw.TextStyle(fontSize: 10.5))),
              pw.Text(rupees(p.$2), style: pw.TextStyle(font: a.bold, fontSize: 10.5)),
            ]),
          ),
        if (t.budget > 0) ...[
          pw.Divider(color: PdfPalette.sage, height: 16),
          row('Budget', rupees(t.budget)),
          row(t.left >= 0 ? 'Left over' : 'Over budget', rupees(t.left.abs()), strong: true),
        ],
      ],
    ),
  );
}

pw.Widget _dayHeader(PlanDay day, pw.TextStyle Function(double, [PdfColor]) display) {
  final date = DateTime.tryParse(day.date);
  final w = day.weather;
  final weather = [
    '${w.tmax}° / ${w.tmin}°',
    if (w.text.isNotEmpty) w.text,
    if (w.rainPct >= 30) 'rain ${w.rainPct}%',
  ].join('  ·  ');
  return pw.Container(
    padding: const pw.EdgeInsets.fromLTRB(14, 10, 14, 10),
    decoration: pw.BoxDecoration(color: PdfPalette.sage, borderRadius: pw.BorderRadius.circular(10)),
    child: pw.Row(
      crossAxisAlignment: pw.CrossAxisAlignment.end,
      children: [
        pw.Expanded(
          child: pw.Column(crossAxisAlignment: pw.CrossAxisAlignment.start, children: [
            pw.Text('DAY ${day.day}',
                style: const pw.TextStyle(fontSize: 8, letterSpacing: 1.4, color: PdfPalette.onPrimary)),
            pw.SizedBox(height: 2),
            pw.Text(date == null ? 'Day ${day.day}' : longDate(date), style: display(18)),
          ]),
        ),
        pw.Column(crossAxisAlignment: pw.CrossAxisAlignment.end, children: [
          pw.Text(weather, style: const pw.TextStyle(fontSize: 9.5, color: PdfPalette.onPrimary)),
          pw.SizedBox(height: 2),
          pw.Text('${day.stops.length} places  ·  ${day.km.toStringAsFixed(1)} km  ·  ${rupees(day.cost)}',
              style: const pw.TextStyle(fontSize: 9.5, color: PdfPalette.onPrimary)),
        ]),
      ],
    ),
  );
}

/// Columns: number, time, place, duration, travel to it, price.
pw.Widget _dayTable(PlanDay day, PdfAssets a) {
  const cell = pw.TextStyle(fontSize: 9.5, color: PdfPalette.slate);
  const head = pw.TextStyle(fontSize: 8, letterSpacing: 1, color: PdfColors.white);
  pw.Widget pad(pw.Widget w) =>
      pw.Padding(padding: const pw.EdgeInsets.symmetric(horizontal: 6, vertical: 6), child: w);
  final rows = <pw.TableRow>[
    pw.TableRow(
      decoration: const pw.BoxDecoration(color: PdfPalette.slate),
      children: [
        for (final h in ['', 'TIME', 'PLACE', 'STAY', 'TRAVEL', 'PRICE']) pad(pw.Text(h, style: head)),
      ],
    ),
  ];
  var n = 0;
  for (final item in day.items) {
    if (!item.isStop) {
      rows.add(pw.TableRow(children: [
        pad(pw.SizedBox()),
        pad(pw.Text('${item.start} – ${item.end}', style: const pw.TextStyle(fontSize: 9, color: PdfPalette.muted))),
        pad(pw.Text(item.name, style: const pw.TextStyle(fontSize: 9, color: PdfPalette.muted))),
        pad(pw.SizedBox()),
        pad(pw.SizedBox()),
        pad(pw.SizedBox()),
      ]));
      continue;
    }
    n++;
    final leg = item.leg;
    final photo = a.photos[item.image];
    rows.add(pw.TableRow(
      verticalAlignment: pw.TableCellVerticalAlignment.middle,
      decoration: pw.BoxDecoration(color: n.isOdd ? PdfPalette.paper : PdfColors.white),
      children: [
        pad(pw.Container(
          width: 18,
          height: 18,
          alignment: pw.Alignment.center,
          decoration: const pw.BoxDecoration(color: PdfPalette.slate, shape: pw.BoxShape.circle),
          child: pw.Text('$n', style: pw.TextStyle(font: a.bold, fontSize: 8, color: PdfColors.white)),
        )),
        pad(pw.Text('${item.start} – ${item.end}',
            style: pw.TextStyle(font: a.bold, fontSize: 9.5, color: PdfPalette.primaryDeep))),
        pad(pw.Row(children: [
          if (photo != null) ...[
            pw.ClipRRect(
              horizontalRadius: 4,
              verticalRadius: 4,
              child: pw.Image(photo, width: 34, height: 34, fit: pw.BoxFit.cover),
            ),
            pw.SizedBox(width: 6),
          ],
          pw.Expanded(
            child: pw.Column(crossAxisAlignment: pw.CrossAxisAlignment.start, children: [
              pw.Text(item.name, style: pw.TextStyle(font: a.bold, fontSize: 10)),
              pw.Text(_title(item.category), style: const pw.TextStyle(fontSize: 8, color: PdfPalette.muted)),
            ]),
          ),
        ])),
        pad(pw.Text(duration(item.minutes), style: cell)),
        pad(pw.Text(
          leg == null
              ? ''
              : '${duration(leg.minutes)}, ${leg.km.toStringAsFixed(1)} km\n${leg.byJeep ? 'Jeep' : rupees(leg.cost)}',
          style: cell,
        )),
        pad(pw.Text(item.costGroup == 0 ? 'Free' : rupees(item.costGroup), style: cell)),
      ],
    ));
  }
  return pw.Table(
    columnWidths: const {
      0: pw.FixedColumnWidth(30),
      1: pw.FixedColumnWidth(78),
      2: pw.FlexColumnWidth(),
      3: pw.FixedColumnWidth(54),
      4: pw.FixedColumnWidth(78),
      5: pw.FixedColumnWidth(56),
    },
    border: const pw.TableBorder(horizontalInside: pw.BorderSide(color: PdfPalette.sand, width: 0.6)),
    children: rows,
  );
}

String _title(String s) => s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);
