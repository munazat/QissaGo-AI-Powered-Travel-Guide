import 'package:flutter/foundation.dart';

/// Where the backend API runs.
///
/// Override when running:  flutter run --dart-define=API_URL=http://192.168.1.5:8000
/// Defaults:
///  - web (Chrome) on your laptop  -> http://localhost:8000
///  - Android emulator             -> http://10.0.2.2:8000  (the emulator's name for your laptop)
class AppConfig {
  static const String _fromBuild = String.fromEnvironment('API_URL');

  static String get apiBase {
    if (_fromBuild.isNotEmpty) return _fromBuild;
    if (kIsWeb) return 'http://localhost:8000';
    if (defaultTargetPlatform == TargetPlatform.android) return 'http://10.0.2.2:8000';
    return 'http://localhost:8000';
  }

  /// Turns a path like /static/images/pois/lhr_fort.jpg into a full URL.
  static String media(String path) {
    if (path.isEmpty) return '';
    if (path.startsWith('http')) return path;
    return '$apiBase$path';
  }
}
