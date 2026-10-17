import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';
import 'package:qissago/core/app_state.dart';
import 'package:qissago/theme.dart';
import 'package:qissago/widgets/media.dart';
import 'package:shared_preferences/shared_preferences.dart';

const testUser = {'id': 1, 'name': 'Ayesha Khan', 'email': 'ayesha@example.com'};

const testMeta = {
  'cities': [
    {'id': 'lahore', 'name': 'Lahore', 'province': 'Punjab', 'image': '', 'description': '', 'places': 28},
    {'id': 'karachi', 'name': 'Karachi', 'province': 'Sindh', 'image': '', 'description': '', 'places': 27},
  ],
  'interests': [
    {'id': 'history', 'label': 'History'},
  ],
  'needs': [
    {'id': 'no_stay', 'label': 'No hotel'},
  ],
};

/// Answers the API calls the app makes, without a server.
http.Client fakeBackend({
  List<Map<String, dynamic>> saved = const [],
  List<Map<String, dynamic>> recent = const [],
  String chatAwaiting = 'city',
  List<Map<String, dynamic>>? generated,
}) {
  return MockClient((req) async {
    final path = req.url.path.replaceFirst('/api/v1', '');
    Object? body;
    if (path == '/auth/login') {
      body = {'token': 't1', 'user': testUser};
    } else if (path == '/auth/me') {
      body = testUser;
    } else if (path == '/meta') {
      body = testMeta;
    } else if (path == '/itineraries') {
      body = saved;
    } else if (path == '/itineraries/recent') {
      body = recent;
    } else if (path == '/itineraries/generate') {
      generated?.add(jsonDecode(req.body) as Map<String, dynamic>);
      body = {'batch_id': 'b1', 'itineraries': [], 'trace': [], 'weather_source': 'seasonal'};
    } else if (path == '/chat/sessions') {
      body = {
        'session_id': 's1',
        'reply': 'Where would you like to go?',
        'suggestions': ['Lahore', 'Karachi'],
        'awaiting': chatAwaiting,
        'ready': false,
        'action': '',
        'preferences': <String, dynamic>{},
      };
    } else {
      return http.Response(jsonEncode({'detail': 'Not found'}), 404);
    }
    return http.Response(jsonEncode(body), 200, headers: {'content-type': 'application/json'});
  });
}

/// A logged-in AppState talking to [fakeBackend].
Future<AppState> signedIn({http.Client? client}) async {
  SharedPreferences.setMockInitialValues({});
  googleFontsEnabled = false;
  videosEnabled = false;
  final state = AppState(client: client ?? fakeBackend());
  await state.init();
  await state.login('ayesha@example.com', 'secret1');
  return state;
}

Widget appWith(AppState state, Widget home) => ChangeNotifierProvider.value(
      value: state,
      child: MaterialApp(theme: buildTheme(), home: home),
    );

/// Sets the test window to [width] x [height] logical pixels for one test.
void setScreen(WidgetTester tester, double width, double height) {
  tester.view.physicalSize = Size(width, height);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
}
