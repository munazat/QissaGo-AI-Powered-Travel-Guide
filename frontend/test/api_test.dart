import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:qissago/core/api.dart';

void main() {
  test('login sends JSON and reads the token', () async {
    final client = MockClient((req) async {
      expect(req.url.path, '/api/v1/auth/login');
      expect(jsonDecode(req.body)['email'], 'a@b.com');
      return http.Response(
        jsonEncode({
          'token': 't123',
          'user': {'id': 1, 'name': 'Ali', 'email': 'a@b.com'},
        }),
        200,
      );
    });
    final api = ApiClient(tokenProvider: () => null, client: client);
    final (token, user) = await api.login('a@b.com', 'secret1');
    expect(token, 't123');
    expect(user.name, 'Ali');
  });

  test('server error message is shown to the user', () async {
    final client = MockClient((_) async => http.Response(jsonEncode({'detail': 'Wrong email or password'}), 401));
    final api = ApiClient(tokenProvider: () => null, client: client);
    expect(
      () => api.login('a@b.com', 'x'),
      throwsA(isA<ApiException>().having((e) => e.message, 'message', 'Wrong email or password')),
    );
  });

  test('token is sent as a Bearer header', () async {
    final client = MockClient((req) async {
      expect(req.headers['Authorization'], 'Bearer abc');
      return http.Response('[]', 200);
    });
    final api = ApiClient(tokenProvider: () => 'abc', client: client);
    expect(await api.saved(), isEmpty);
  });
  test('replanning API sends preview and apply requests', () async {
    final requests = <http.Request>[];
    final client = MockClient((req) async {
      requests.add(req);
      return http.Response(
        jsonEncode({
          'itinerary_id': 'trip-1',
          'version': req.url.path.endsWith('/preview') ? 0 : 2,
          'plan': {'days': []},
          'diff': {
            'affected_days': [1],
            'reason': 'remove'
          },
          'trace': [],
        }),
        200,
      );
    });
    final api = ApiClient(tokenProvider: () => 'abc', client: client);

    final preview = await api.previewReplan('trip-1', 'remove stop fort on day 1');
    final applied = await api.replan('trip-1', 'remove stop fort on day 1');

    expect(preview.version, 0);
    expect(applied.version, 2);
    expect(requests.map((request) => request.url.path), [
      '/api/v1/itineraries/trip-1/replan/preview',
      '/api/v1/itineraries/trip-1/replan',
    ]);
    expect(jsonDecode(requests.first.body)['request_text'], 'remove stop fort on day 1');
  });

  test('progress and weather suggestion responses are parsed', () async {
    final client = MockClient((req) async {
      if (req.method == 'PUT') {
        expect(req.url.path, '/api/v1/itineraries/trip-1/progress');
        expect(jsonDecode(req.body)['current_time'], '14:00');
        return http.Response(
            jsonEncode({
              'day': 1,
              'completed_stop_ids': ['fort']
            }),
            200);
      }
      expect(req.url.path, '/api/v1/itineraries/trip-1/weather-suggestions');
      return http.Response(
        jsonEncode({
          'suggestions': [
            {
              'day': 1,
              'stop_id': 'fort',
              'stop_name': 'Fort',
              'message': 'Rain is likely',
              'suggested_place_id': 'museum',
              'suggested_place_name': 'Museum',
            }
          ]
        }),
        200,
      );
    });
    final api = ApiClient(tokenProvider: () => 'abc', client: client);

    final progress = await api.updateProgress('trip-1', {
      'day': 1,
      'completed_stop_ids': ['fort'],
      'current_time': '14:00',
    });
    final suggestions = await api.weatherSuggestions('trip-1');

    expect(progress['completed_stop_ids'], ['fort']);
    expect(suggestions.single['suggested_place_id'], 'museum');
  });

  test('version listing and restore parse the response', () async {
    final client = MockClient((req) async {
      if (req.url.path.endsWith('/versions')) {
        return http.Response(
          jsonEncode([
            {'id': 4, 'version': 2, 'reason': 'restore:1', 'created_at': '2026-11-09T10:00:00Z'}
          ]),
          200,
        );
      }
      expect(req.url.path, '/api/v1/itineraries/trip-1/versions/restore');
      expect(jsonDecode(req.body)['version'], 1);
      return http.Response(
        jsonEncode({
          'itinerary_id': 'trip-1',
          'version': 3,
          'plan': {'days': []},
          'diff': {'affected_days': [], 'reason': 'restore:1'},
          'trace': [],
        }),
        200,
      );
    });
    final api = ApiClient(tokenProvider: () => 'abc', client: client);

    final versions = await api.versions('trip-1');
    final restored = await api.restoreVersion('trip-1', 1);

    expect(versions.single['version'], 2);
    expect(restored.version, 3);
  });
}
