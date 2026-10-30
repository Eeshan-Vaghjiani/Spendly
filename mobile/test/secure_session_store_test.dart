import 'dart:async';
import 'dart:convert';

import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:spending_support/data/repositories/api_spending_repository.dart';
import 'package:spending_support/data/services/api_client.dart';
import 'package:spending_support/data/services/token_store.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'widget_test.dart' show FakeGoogleIdentity;

class FixtureSecureStorage extends FlutterSecureStorage {
  final values = <String, String>{};
  bool failWrite = false, failDelete = false, failRead = false;
  Completer<void>? writeGate, writeStarted;
  @override
  Future<void> write({
    required String key,
    required String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (failWrite) throw PlatformException(code: 'fixture-write');
    final gate = writeGate;
    if (gate != null) {
      writeGate = null;
      writeStarted?.complete();
      await gate.future;
    }
    if (value == null) {
      values.remove(key);
    } else {
      values[key] = value;
    }
  }

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (failRead) throw PlatformException(code: 'fixture-read');
    return values[key];
  }

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (failDelete) throw PlatformException(code: 'fixture-delete');
    values.remove(key);
  }
}

const oldUser = {
  'id': 'synthetic-alpha',
  'email': 'alpha@example.invalid',
  'display_name': 'Alpha',
  'has_required_consents': true,
};
const newUser = {
  'id': 'synthetic-beta',
  'email': 'beta@example.invalid',
  'display_name': 'Beta',
  'has_required_consents': true,
};
http.Response fixtureResponse(Map<String, dynamic> data) =>
    http.Response(jsonEncode({'success': true, 'data': data}), 200);

void main() {
  test(
    'actual storage read failure can retry offline without deleting the stored pair',
    () async {
      final fixture = FixtureSecureStorage();
      final store = SecureTokenStore(storage: fixture);
      await store.writeSession('synthetic-alpha-token', jsonEncode(oldUser));
      final before = Map<String, String>.from(fixture.values);
      fixture.failRead = true;
      final repository = ApiSpendingRepository(
        ApiClient(
          baseUrl: 'http://localhost',
          tokenStore: store,
          httpClient: MockClient(
            (_) async => throw http.ClientException('fixture offline'),
          ),
        ),
      );
      final auth = AuthController(repository, FakeGoogleIdentity());
      addTearDown(auth.dispose);
      await Future<void>.delayed(Duration.zero);
      expect(auth.state.initialized, false);
      expect(auth.state.loading, false);
      expect(auth.state.error, contains('Could not open'));
      expect(fixture.values, before);
      fixture.failRead = false;
      await auth.restore();
      expect(auth.state.user?.id, 'synthetic-alpha');
      expect(auth.state.initialized, true);
      expect(fixture.values, before);
    },
  );
  test(
    'legacy complete pair migrates as one record and survives a new wrapper',
    () async {
      final fixture = FixtureSecureStorage()
        ..values.addAll({
          'access_token': 'synthetic-alpha-token',
          'signed_in_user': jsonEncode(oldUser),
        });
      final store = SecureTokenStore(storage: fixture);
      expect(await store.read(), 'synthetic-alpha-token');
      expect(jsonDecode((await store.readUser())!)['id'], 'synthetic-alpha');
      await store.writeSession('synthetic-beta-token', jsonEncode(newUser));
      expect(fixture.values.containsKey('access_token'), false);
      expect(fixture.values.containsKey('signed_in_user'), false);
      final restarted = SecureTokenStore(storage: fixture);
      expect(await restarted.read(), 'synthetic-beta-token');
      expect(jsonDecode((await restarted.readUser())!)['id'], 'synthetic-beta');
    },
  );

  test('an incomplete legacy pair is not restored', () async {
    final fixture = FixtureSecureStorage()
      ..values['access_token'] = 'synthetic-orphan-token';
    final store = SecureTokenStore(storage: fixture);
    expect(await store.read(), isNull);
    expect(await store.readUser(), isNull);
  });

  test('failed session replacement keeps a complete previous record', () async {
    final fixture = FixtureSecureStorage();
    final store = SecureTokenStore(storage: fixture);
    await store.writeSession('synthetic-alpha-token', jsonEncode(oldUser));
    fixture.failWrite = true;
    await expectLater(
      store.writeSession('synthetic-beta-token', jsonEncode(newUser)),
      throwsA(isA<PlatformException>()),
    );
    final restarted = SecureTokenStore(storage: fixture);
    expect(await restarted.read(), 'synthetic-alpha-token');
    expect(jsonDecode((await restarted.readUser())!)['id'], 'synthetic-alpha');
  });

  test(
    'failed signin write cannot create a partial restorable session after restart',
    () async {
      final fixture = FixtureSecureStorage();
      final store = SecureTokenStore(storage: fixture);
      await store.writeSession('synthetic-alpha-token', jsonEncode(oldUser));
      await store.clear();
      fixture.failWrite = true;
      final repository = ApiSpendingRepository(
        ApiClient(
          baseUrl: 'http://localhost',
          tokenStore: store,
          httpClient: MockClient(
            (_) async => fixtureResponse({
              'access_token': 'synthetic-beta-token',
              'user': newUser,
            }),
          ),
        ),
      );
      await expectLater(
        repository.login('beta@example.invalid', 'synthetic-only'),
        throwsA(isA<PlatformException>()),
      );
      var renewed = false;
      final restarted = ApiSpendingRepository(
        ApiClient(
          baseUrl: 'http://localhost',
          tokenStore: SecureTokenStore(storage: fixture),
          httpClient: MockClient((_) async {
            renewed = true;
            return fixtureResponse({
              'access_token': 'synthetic-beta-token',
              'user': newUser,
            });
          }),
        ),
      );
      expect(await restarted.restoreSession(), isNull);
      expect(renewed, false);
    },
  );

  test(
    'logout tombstone prevents legacy resurrection when obsolete-key deletion fails',
    () async {
      final fixture = FixtureSecureStorage()
        ..values.addAll({
          'access_token': 'synthetic-alpha-token',
          'signed_in_user': jsonEncode(oldUser),
        })
        ..failDelete = true;
      await SecureTokenStore(storage: fixture).clear();
      expect(fixture.values.containsKey('access_token'), true);
      final restarted = SecureTokenStore(storage: fixture);
      expect(await restarted.read(), isNull);
      expect(await restarted.readUser(), isNull);
    },
  );

  test(
    'failed authoritative logout write preserves the current complete session',
    () async {
      final fixture = FixtureSecureStorage();
      final store = SecureTokenStore(storage: fixture);
      await store.writeSession('synthetic-alpha-token', jsonEncode(oldUser));
      fixture.failWrite = true;
      await expectLater(store.clear(), throwsA(isA<PlatformException>()));
      expect(await store.read(), 'synthetic-alpha-token');
      expect(jsonDecode((await store.readUser())!)['id'], 'synthetic-alpha');
    },
  );

  for (final value in [
    'invalid-json',
    '{"signed_out":true}',
    '{"token":"orphan"}',
  ]) {
    test(
      'present invalid or signed-out record never falls back to legacy ($value)',
      () async {
        final fixture = FixtureSecureStorage()
          ..values.addAll({
            'access_token': 'synthetic-alpha-token',
            'signed_in_user': jsonEncode(oldUser),
            'signed_in_session_v2': value,
          });
        expect(await SecureTokenStore(storage: fixture).read(), isNull);
        expect(await SecureTokenStore(storage: fixture).readUser(), isNull);
      },
    );
  }

  test(
    'separate secure wrappers serialize an in-flight old write before logout/new signin',
    () async {
      final fixture = FixtureSecureStorage();
      final store = SecureTokenStore(storage: fixture);
      await store.writeSession('synthetic-alpha-token', jsonEncode(oldUser));
      final firstApi = ApiClient(
        baseUrl: 'http://localhost',
        tokenStore: store,
        httpClient: MockClient((_) async => fixtureResponse(oldUser)),
      );
      final first = ApiSpendingRepository(firstApi);
      final gate = Completer<void>();
      fixture.writeGate = gate;
      fixture.writeStarted = Completer<void>();
      final old = first
          .updateUsername('alpha_changed')
          .then<Object?>((value) => value, onError: (Object error) => error);
      await fixture.writeStarted!.future;
      firstApi.close();
      final second = ApiSpendingRepository(
        ApiClient(
          baseUrl: 'http://localhost',
          tokenStore: SecureTokenStore(storage: fixture),
          httpClient: MockClient(
            (_) async => fixtureResponse({
              'access_token': 'synthetic-beta-token',
              'user': newUser,
            }),
          ),
        ),
      );
      final logout = second.logout();
      final signin = second.login('beta@example.invalid', 'synthetic-only');
      gate.complete();
      await logout;
      await signin;
      await old;
      final restarted = SecureTokenStore(storage: fixture);
      expect(await restarted.read(), 'synthetic-beta-token');
      expect(jsonDecode((await restarted.readUser())!)['id'], 'synthetic-beta');
    },
  );
}
