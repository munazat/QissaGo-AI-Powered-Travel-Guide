import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'api.dart';
import 'models.dart';

/// App-wide state: who is logged in, the city/interest options, and display settings.
class AppState extends ChangeNotifier {
  AppState({http.Client? client}) {
    api = ApiClient(tokenProvider: () => _token, client: client);
  }

  late final ApiClient api;
  String? _token;
  AppUser? user;
  Meta? meta;
  bool loading = true;

  /// Goes up whenever a trip is saved or unsaved, so lists showing saved trips reload.
  int savedVersion = 0;

  /// Which details are shown on each stop (the user can switch them on/off).
  static const toggleKeys = ['time', 'travel', 'price', 'weather', 'map', 'photos'];
  final Map<String, bool> show = {for (final k in toggleKeys) k: true};

  bool get loggedIn => _token != null && user != null;

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('token');
    final userJson = prefs.getString('user');
    if (userJson != null) user = AppUser.fromJson(jsonDecode(userJson));
    for (final k in toggleKeys) {
      show[k] = prefs.getBool('show_$k') ?? true;
    }
    if (_token != null) {
      try {
        user = await api.me();
      } on ApiException catch (e) {
        if (e.status == 401) await _clear();
      }
    }
    await loadMeta();
    loading = false;
    notifyListeners();
  }

  Future<void> loadMeta() async {
    try {
      meta = await api.meta();
    } on ApiException {
      meta = null;
    }
    notifyListeners();
  }

  Future<void> _store(String token, AppUser u) async {
    _token = token;
    user = u;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', token);
    await prefs.setString('user', jsonEncode(u.toJson()));
    if (meta == null) await loadMeta();
    notifyListeners();
  }

  Future<void> login(String email, String password) async {
    final (token, u) = await api.login(email.trim(), password);
    await _store(token, u);
  }

  Future<void> register(String name, String email, String password) async {
    final (token, u) = await api.register(name.trim(), email.trim(), password);
    await _store(token, u);
  }

  Future<void> _clear() async {
    _token = null;
    user = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
    await prefs.remove('user');
  }

  Future<void> logout() async {
    await _clear();
    notifyListeners();
  }

  void savedChanged() {
    savedVersion++;
    notifyListeners();
  }

  Future<void> setShow(String key, bool value) async {
    show[key] = value;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('show_$key', value);
  }
}
