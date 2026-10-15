import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// QissaGo colours. Contrast ratios are for normal text (WCAG AA needs 4.5:1).
class Palette {
  /// Sea green: buttons, active tabs, highlights, map route. Never used for text.
  static const primary = Color(0xFF8FBC8F);

  /// Darker sea green for text and icons on light backgrounds (4.8:1 on sand).
  static const primaryDeep = Color(0xFF3E6B4E);

  /// Deep slate: main text, headings, dark overlays on photos, app bars (7:1 on sand).
  static const slate = Color(0xFF2F4F4F);

  /// Text on sea green and terracotta (5.8:1 or better).
  static const onPrimary = Color(0xFF1F3636);

  /// Warm sand: page background.
  static const sand = Color(0xFFE8E4D8);

  /// Sage: cards, chips, input fields, secondary surfaces.
  static const sage = Color(0xFFC7D3C0);

  /// Terracotta: match score, Best match badge, small highlights.
  static const terracotta = Color(0xFFD9A38F);

  /// Deeper terracotta, used where a chart needs a fifth distinct colour.
  static const terracottaDeep = Color(0xFFA86F5C);

  /// Light sage-grey, the sixth colour in the cost bar.
  static const stone = Color(0xFFB7C2AF);

  /// Secondary text (5.8:1 on sand, 4.8:1 on sage).
  static const muted = Color(0xFF435A56);

  /// Thin borders and dividers.
  static const line = Color(0xFFB7C2AF);

  /// Light raised surface (sheets, dialogs, the bottom bar).
  static const paper = Color(0xFFF4F1EA);

  static const ink = slate;

  static const heroGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF3D6363), slate],
  );

  /// Slate gradient laid over photos so white text stays readable.
  static LinearGradient photoShade({double top = 0.15, double bottom = 0.9, double start = 0.3}) => LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        stops: [start, 1],
        colors: [slate.withValues(alpha: top), slate.withValues(alpha: bottom)],
      );
}

/// Widget tests switch this off so no fonts are downloaded.
bool googleFontsEnabled = true;

TextStyle display(double size, {Color color = Palette.slate, bool? useGoogleFonts}) {
  final base = TextStyle(fontSize: size, color: color, height: 1.1, fontWeight: FontWeight.w400);
  return (useGoogleFonts ?? googleFontsEnabled) ? GoogleFonts.dmSerifDisplay(textStyle: base) : base;
}

/// Small caps label above a group of controls.
const labelStyle = TextStyle(fontSize: 12, letterSpacing: 1.2, fontWeight: FontWeight.w800, color: Palette.muted);

ThemeData buildTheme({bool? useGoogleFonts}) {
  useGoogleFonts ??= googleFontsEnabled;
  const scheme = ColorScheme(
    brightness: Brightness.light,
    primary: Palette.primary,
    onPrimary: Palette.onPrimary,
    primaryContainer: Palette.sage,
    onPrimaryContainer: Palette.onPrimary,
    secondary: Palette.slate,
    onSecondary: Colors.white,
    secondaryContainer: Palette.sage,
    onSecondaryContainer: Palette.onPrimary,
    tertiary: Palette.terracotta,
    onTertiary: Palette.onPrimary,
    error: Color(0xFF9E3B2C),
    onError: Colors.white,
    surface: Palette.sand,
    onSurface: Palette.slate,
    onSurfaceVariant: Palette.muted,
    surfaceContainerLowest: Palette.paper,
    surfaceContainerLow: Palette.paper,
    surfaceContainer: Palette.paper,
    surfaceContainerHigh: Palette.paper,
    surfaceContainerHighest: Palette.sage,
    outline: Palette.line,
    outlineVariant: Palette.line,
  );
  final base = ThemeData(useMaterial3: true, colorScheme: scheme, scaffoldBackgroundColor: Palette.sand);
  final text = useGoogleFonts ? GoogleFonts.plusJakartaSansTextTheme(base.textTheme) : base.textTheme;
  final shape16 = RoundedRectangleBorder(borderRadius: BorderRadius.circular(16));
  return base.copyWith(
    textTheme: text.apply(bodyColor: Palette.slate, displayColor: Palette.slate),
    appBarTheme: const AppBarTheme(
      backgroundColor: Palette.sand,
      foregroundColor: Palette.slate,
      surfaceTintColor: Colors.transparent,
      scrolledUnderElevation: 0,
      elevation: 0,
    ),
    pageTransitionsTheme: const PageTransitionsTheme(
      builders: {
        TargetPlatform.android: FadeForwardsPageTransitionsBuilder(),
        TargetPlatform.iOS: FadeForwardsPageTransitionsBuilder(),
        TargetPlatform.windows: FadeForwardsPageTransitionsBuilder(),
        TargetPlatform.linux: FadeForwardsPageTransitionsBuilder(),
        TargetPlatform.macOS: FadeForwardsPageTransitionsBuilder(),
        TargetPlatform.fuchsia: FadeForwardsPageTransitionsBuilder(),
      },
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: Palette.primary,
        foregroundColor: Palette.onPrimary,
        disabledBackgroundColor: Palette.sage,
        disabledForegroundColor: Palette.muted,
        minimumSize: const Size(64, 52),
        shape: shape16,
        textStyle: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: Palette.slate,
        minimumSize: const Size(64, 48),
        side: const BorderSide(color: Palette.line, width: 1.2),
        shape: shape16,
        textStyle: const TextStyle(fontWeight: FontWeight.w700),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(
        foregroundColor: Palette.primaryDeep,
        minimumSize: const Size(48, 44),
        textStyle: const TextStyle(fontWeight: FontWeight.w800),
      ),
    ),
    segmentedButtonTheme: SegmentedButtonThemeData(
      style: SegmentedButton.styleFrom(
        backgroundColor: Palette.paper,
        foregroundColor: Palette.slate,
        selectedBackgroundColor: Palette.primary,
        selectedForegroundColor: Palette.onPrimary,
        side: const BorderSide(color: Palette.line),
        minimumSize: const Size(0, 44),
        textStyle: const TextStyle(fontWeight: FontWeight.w800),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: Palette.sage,
      selectedColor: Palette.primary,
      side: BorderSide.none,
      shape: const StadiumBorder(),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      labelStyle: const TextStyle(color: Palette.onPrimary, fontWeight: FontWeight.w700),
      checkmarkColor: Palette.onPrimary,
    ),
    sliderTheme: const SliderThemeData(
      activeTrackColor: Palette.primaryDeep,
      inactiveTrackColor: Palette.sage,
      thumbColor: Palette.primaryDeep,
      valueIndicatorColor: Palette.slate,
    ),
    switchTheme: SwitchThemeData(
      thumbColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? Palette.slate : null),
      trackColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? Palette.primary : null),
    ),
    progressIndicatorTheme: const ProgressIndicatorThemeData(color: Palette.primaryDeep),
    bottomSheetTheme: const BottomSheetThemeData(
      backgroundColor: Palette.paper,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(28))),
    ),
    dialogTheme: const DialogThemeData(backgroundColor: Palette.paper, surfaceTintColor: Colors.transparent),
    datePickerTheme: const DatePickerThemeData(
      backgroundColor: Palette.paper,
      surfaceTintColor: Colors.transparent,
      headerBackgroundColor: Palette.slate,
      headerForegroundColor: Colors.white,
    ),
    snackBarTheme: const SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      backgroundColor: Palette.slate,
      contentTextStyle: TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
    ),
    dividerTheme: const DividerThemeData(color: Palette.line),
    tooltipTheme: const TooltipThemeData(
      decoration: BoxDecoration(color: Palette.slate, borderRadius: BorderRadius.all(Radius.circular(8))),
      textStyle: TextStyle(color: Colors.white),
    ),
  );
}

/// Text field style used across the app.
InputDecoration fieldStyle(String label, {IconData? icon}) => InputDecoration(
      labelText: label,
      labelStyle: const TextStyle(color: Palette.muted),
      prefixIcon: icon == null ? null : Icon(icon, color: Palette.muted),
      filled: true,
      fillColor: Palette.sage.withValues(alpha: 0.55),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: BorderSide.none),
      focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: Palette.slate, width: 1.6)),
    );
