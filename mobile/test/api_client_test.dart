import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:spending_support/core/network/api_exception.dart';
import 'package:spending_support/data/repositories/api_spending_repository.dart';
import 'package:spending_support/data/services/api_client.dart';
import 'package:spending_support/data/services/token_store.dart';

class MemoryTokenStore implements TokenStore {
  String? token;
  String? userJson;

  @override
  Future<void> clear() async {
    token = null;
    userJson = null;
  }

  @override
  Future<String?> read() async => token;

  @override
  Future<String?> readUser() async => userJson;

  @override
  Future<void> write(String token) async => this.token = token;

  @override
  Future<void> writeUser(String userJson) async => this.userJson = userJson;
}

void main() {
  test(
    'ambiguous write responses advise checking rather than resubmitting',
    () async {
      for (final status in [502, 200]) {
        var calls = 0;
        final api = ApiClient(
          baseUrl: 'http://localhost',
          tokenStore: MemoryTokenStore(),
          httpClient: MockClient((_) async {
            calls++;
            return http.Response('<html>gateway</html>', status);
          }),
        );
        await expectLater(
          api.request('POST', '/transactions'),
          throwsA(
            isA<ApiException>().having(
              (e) => e.message,
              'uncertain write',
              contains('may have been saved'),
            ),
          ),
        );
        expect(calls, 1);
      }
    },
  );
  test(
    'network failures are safe after read retry and mutation is not retried',
    () async {
      for (final method in ['GET', 'POST', 'PUT', 'DELETE']) {
        var calls = 0;
        final api = ApiClient(
          baseUrl: 'http://private-host/api/v1',
          tokenStore: MemoryTokenStore(),
          httpClient: MockClient((_) async {
            calls++;
            throw http.ClientException(
              'SocketException secret diagnostic',
              Uri.parse('http://private-host'),
            );
          }),
        );
        await expectLater(
          api.request(method, '/transactions'),
          throwsA(
            isA<ApiException>()
                .having((e) => e.code, 'code', 'NETWORK_ERROR')
                .having(
                  (e) => e.toString(),
                  'safe text',
                  isNot(contains('private-host')),
                )
                .having(
                  (e) => e.toString(),
                  'no raw exception',
                  isNot(contains('SocketException')),
                ),
          ),
        );
        expect(calls, method == 'GET' ? 2 : 1);
      }
    },
  );

  test('read retry succeeds and opt-out makes one attempt', () async {
    var calls = 0;
    final api = ApiClient(
      baseUrl: 'http://localhost',
      tokenStore: MemoryTokenStore(),
      httpClient: MockClient((_) async {
        if (++calls == 1) throw const SocketException('private diagnostic');
        return http.Response('{"data":{"total":1}}', 200);
      }),
    );
    expect((await api.request('GET', '/transactions'))['total'], 1);
    calls = 0;
    await expectLater(
      api.request('GET', '/transactions', retryOnce: false),
      throwsA(isA<ApiException>()),
    );
    expect(calls, 1);
  });

  test(
    'write timeout is bounded and warns against duplicate submission',
    () async {
      var calls = 0;
      final pending = Completer<http.Response>();
      final api = ApiClient(
        baseUrl: 'http://localhost',
        tokenStore: MemoryTokenStore(),
        requestTimeout: const Duration(milliseconds: 10),
        httpClient: MockClient((_) {
          calls++;
          return pending.future;
        }),
      );
      await expectLater(
        api.request('POST', '/transactions'),
        throwsA(
          isA<ApiException>()
              .having((e) => e.code, 'code', 'REQUEST_TIMEOUT')
              .having(
                (e) => e.message,
                'uncertain write',
                contains('may have been saved'),
              ),
        ),
      );
      expect(calls, 1);
      pending.complete(http.Response('{"data":{}}', 200));
    },
  );

  test(
    'HTML gateway and malformed responses never leak technical details',
    () async {
      for (final status in [503, 401, 200]) {
        final api = ApiClient(
          baseUrl: 'http://localhost',
          tokenStore: MemoryTokenStore(),
          httpClient: MockClient(
            (_) async => http.Response(
              '<html>private upstream diagnostic</html>',
              status,
            ),
          ),
        );
        await expectLater(
          api.request('GET', '/transactions'),
          throwsA(
            isA<ApiException>()
                .having(
                  (e) => e.toString(),
                  'safe text',
                  isNot(contains('private')),
                )
                .having(
                  (e) => e.code,
                  'code',
                  status == 503
                      ? 'SERVICE_UNAVAILABLE'
                      : status == 401
                      ? 'HTTP_ERROR'
                      : 'INVALID_RESPONSE',
                ),
          ),
        );
      }
    },
  );

  test(
    'CSV upload uses authenticated shared transport and safe network errors',
    () async {
      final directory = Directory.systemTemp.createTempSync(
        'spendly_upload_test_',
      );
      addTearDown(() => directory.deleteSync(recursive: true));
      final file = File('${directory.path}/fixture.csv')
        ..writeAsStringSync('amount\n100\n');
      var calls = 0;
      final api = ApiClient(
        baseUrl: 'http://localhost/api/v1',
        tokenStore: MemoryTokenStore()..token = 'fixture',
        httpClient: MockClient((request) async {
          calls++;
          expect(request.headers['authorization'], 'Bearer fixture');
          expect(
            request.headers['content-type'],
            contains('multipart/form-data'),
          );
          expect(request.body, contains('fixture.csv'));
          throw http.ClientException('private upload URL');
        }),
      );
      await expectLater(
        api.uploadCsv(file.path),
        throwsA(
          isA<ApiException>().having((e) => e.code, 'code', 'NETWORK_ERROR'),
        ),
      );
      expect(calls, 1);
      await expectLater(
        api.uploadCsv('${directory.path}/missing.csv'),
        throwsA(
          isA<ApiException>().having((e) => e.code, 'code', 'FILE_UNAVAILABLE'),
        ),
      );
    },
  );

  test('API client sends bearer token and decodes data', () async {
    final store = MemoryTokenStore()..token = 'abc';
    final client = MockClient((request) async {
      expect(request.headers['authorization'], 'Bearer abc');
      expect(request.url.path, '/api/v1/transactions');
      return http.Response(
        jsonEncode({
          'success': true,
          'data': {'items': <dynamic>[], 'total': 0},
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final api = ApiClient(
      baseUrl: 'http://localhost/api/v1',
      tokenStore: store,
      httpClient: client,
    );
    final data = await api.request('GET', '/transactions');
    expect(data['total'], 0);
  });

  test('API client preserves the shared backend error contract', () async {
    final client = MockClient(
      (_) async => http.Response(
        jsonEncode({
          'success': false,
          'error': {
            'code': 'INSUFFICIENT_HISTORY',
            'message': 'More history is required.',
          },
        }),
        422,
      ),
    );
    final api = ApiClient(
      baseUrl: 'http://localhost/api/v1',
      tokenStore: MemoryTokenStore(),
      httpClient: client,
    );
    expect(
      () => api.request('POST', '/analysis/run', body: {}),
      throwsA(
        isA<ApiException>()
            .having((error) => error.code, 'code', 'INSUFFICIENT_HISTORY')
            .having((error) => error.statusCode, 'status', 422),
      ),
    );
  });

  test(
    'temporary backend failure keeps the cached signed-in session',
    () async {
      final store = MemoryTokenStore()
        ..token = 'still-valid'
        ..userJson = jsonEncode({
          'id': 'user-1',
          'email': 'eva@example.com',
          'display_name': 'Eva',
          'has_required_consents': true,
          'model_training_opt_in': false,
        });
      final repository = ApiSpendingRepository(
        ApiClient(
          baseUrl: 'http://localhost/api/v1',
          tokenStore: store,
          httpClient: MockClient(
            (_) async => throw http.ClientException('Backend is restarting'),
          ),
        ),
      );

      final restored = await repository.restoreSession();

      expect(restored?.email, 'eva@example.com');
      expect(store.token, 'still-valid');
    },
  );

  test('invalid token clears the saved session', () async {
    final store = MemoryTokenStore()
      ..token = 'expired'
      ..userJson = jsonEncode({
        'id': 'user-1',
        'email': 'eva@example.com',
        'display_name': 'Eva',
      });
    final repository = ApiSpendingRepository(
      ApiClient(
        baseUrl: 'http://localhost/api/v1',
        tokenStore: store,
        httpClient: MockClient(
          (_) async => http.Response(
            jsonEncode({
              'success': false,
              'error': {
                'code': 'TOKEN_EXPIRED',
                'message': 'The access token has expired.',
              },
            }),
            401,
          ),
        ),
      ),
    );

    expect(await repository.restoreSession(), isNull);
    expect(store.token, isNull);
    expect(store.userJson, isNull);
  });
}
