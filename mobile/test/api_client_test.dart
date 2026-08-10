import 'dart:convert';

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
