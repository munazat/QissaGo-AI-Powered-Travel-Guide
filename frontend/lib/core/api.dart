import 'dart:convert';

import 'package:http/http.dart' as http;

import 'config.dart';
import 'models.dart';

class ApiException implements Exception {
  final String message;
  final int status;

  ApiException(this.message, [this.status = 0]);

  @override
  String toString() => message;
}

/// Every call to the backend goes through this class.
class ApiClient {
  ApiClient({required this.tokenProvider, http.Client? client}) : _http = client ?? http.Client();

  final String? Function() tokenProvider;
  final http.Client _http;
  static const _timeout = Duration(seconds: 60);

  Uri _uri(String path) => Uri.parse('${AppConfig.apiBase}/api/v1$path');

  Map<String, String> get _headers {
    final token = tokenProvider();
    return {
      'Content-Type': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
    };
  }

  Future<dynamic> _send(Future<http.Response> Function() request) async {
    http.Response r;
    try {
      r = await request().timeout(_timeout);
    } catch (_) {
      throw ApiException('Cannot reach the server');
    }
    final body = r.body.isEmpty ? null : jsonDecode(utf8.decode(r.bodyBytes));
    if (r.statusCode >= 200 && r.statusCode < 300) return body;
    var message = 'Something went wrong';
    if (body is Map && body['detail'] != null) {
      final d = body['detail'];
      if (d is String) {
        message = d;
      } else if (d is List && d.isNotEmpty && d.first is Map) {
        message = (d.first as Map)['msg']?.toString() ?? message;
      }
    }
    throw ApiException(message, r.statusCode);
  }

  Future<dynamic> get(String path) => _send(() => _http.get(_uri(path), headers: _headers));

  Future<dynamic> post(String path, [Object? body]) =>
      _send(() => _http.post(_uri(path), headers: _headers, body: jsonEncode(body ?? {})));

  Future<dynamic> delete(String path) => _send(() => _http.delete(_uri(path), headers: _headers));

  // ---------------------------------------------------------------- auth
  Future<(String, AppUser)> login(String email, String password) async {
    final j = await post('/auth/login', {'email': email, 'password': password});
    return (j['token'] as String, AppUser.fromJson(j['user']));
  }

  Future<(String, AppUser)> register(String name, String email, String password) async {
    final j = await post('/auth/register', {'name': name, 'email': email, 'password': password});
    return (j['token'] as String, AppUser.fromJson(j['user']));
  }

  Future<AppUser> me() async => AppUser.fromJson(await get('/auth/me'));

  // ---------------------------------------------------------------- data
  Future<Meta> meta() async => Meta.fromJson(await get('/meta'));

  // ---------------------------------------------------------------- chat
  Future<ChatTurn> startChat() async => ChatTurn.fromJson(await post('/chat/sessions'));

  Future<ChatTurn> sendChat(String sessionId, {String? text, Map<String, dynamic>? patch}) async {
    final j = await post('/chat/sessions/$sessionId/messages', {
      if (text != null) 'text': text,
      if (patch != null) 'patch': patch,
    });
    return ChatTurn.fromJson(j);
  }

  // ---------------------------------------------------------------- itineraries
  Future<List<Itinerary>> generate({String? sessionId, Map<String, dynamic>? preferences}) async {
    final j = await post('/itineraries/generate', {
      if (sessionId != null) 'session_id': sessionId,
      if (preferences != null) 'preferences': preferences,
    });
    return (j['itineraries'] as List).map((e) => Itinerary.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<List<Itinerary>> saved() async =>
      (await get('/itineraries') as List).map((e) => Itinerary.fromJson(e as Map<String, dynamic>)).toList();

  /// Best option of each recent plan batch.
  Future<List<Itinerary>> recent() async =>
      (await get('/itineraries/recent') as List).map((e) => Itinerary.fromJson(e as Map<String, dynamic>)).toList();

  Future<List<Itinerary>> batch(String batchId) async => (await get('/itineraries/batch/$batchId') as List)
      .map((e) => Itinerary.fromJson(e as Map<String, dynamic>))
      .toList();

  Future<Itinerary> itinerary(String id) async => Itinerary.fromJson(await get('/itineraries/$id'));

  Future<void> save(String id) => post('/itineraries/$id/save');

  Future<void> unsave(String id) => delete('/itineraries/$id/save');
}
