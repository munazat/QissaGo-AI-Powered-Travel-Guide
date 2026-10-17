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
}
