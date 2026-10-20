import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../../core/network/api_exception.dart';
import 'token_store.dart';

class _SessionStorage {
  int generation = 0;
  Future<void> _tail = Future.value();

  Future<T> run<T>(Future<T> Function() operation) {
    final result = _tail.then((_) => operation());
    _tail = result.then<void>((_) {}, onError: (Object _, StackTrace _) {});
    return result;
  }
}

class ApiClient {
  ApiClient({
    required this.baseUrl,
    required TokenStore tokenStore,
    http.Client? httpClient,
    this.requestTimeout = const Duration(seconds: 30),
    this.uploadTimeout = const Duration(minutes: 2),
  }) : _tokenStore = tokenStore,
       _session =
           _sessions[tokenStore is SecureTokenStore
                   ? SecureTokenStore.sessionScope
                   : tokenStore] ??=
               _SessionStorage(),
       _httpClient = httpClient ?? http.Client();

  static final _sessions = Expando<_SessionStorage>();
  final _SessionStorage _session;
  bool _closed = false;
  final String baseUrl;
  final TokenStore _tokenStore;
  final http.Client _httpClient;
  final Duration requestTimeout;
  final Duration uploadTimeout;

  Future<Map<String, dynamic>> request(
    String method,
    String path, {
    Map<String, dynamic>? body,
    bool authenticated = true,
    bool retryOnce = true,
  }) async {
    final generation = sessionGeneration;
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (authenticated) {
      final token = await readToken();
      _requireSession(generation);
      if (token != null) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    final uri = Uri.parse('$baseUrl$path');
    Future<http.Response> send() {
      if (authenticated) _requireSession(generation);
      switch (method) {
        case 'GET':
          return _httpClient.get(uri, headers: headers);
        case 'POST':
          return _httpClient.post(
            uri,
            headers: headers,
            body: body == null ? null : jsonEncode(body),
          );
        case 'PUT':
          return _httpClient.put(
            uri,
            headers: headers,
            body: body == null ? null : jsonEncode(body),
          );
        case 'DELETE':
          return _httpClient.delete(uri, headers: headers);
        default:
          throw ArgumentError('Unsupported HTTP method: $method');
      }
    }

    final response = await _transport(
      () => send().timeout(requestTimeout),
      retryRead: method == 'GET' && retryOnce,
      mutation: method != 'GET',
    );
    if (authenticated) _requireSession(generation);
    return _decode(response, mutation: method != 'GET');
  }

  Future<Map<String, dynamic>> uploadCsv(String filePath) async {
    final generation = sessionGeneration;
    final upload = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/transactions/upload'),
    );
    final token = await readToken();
    _requireSession(generation);
    if (token != null) {
      upload.headers['Authorization'] = 'Bearer $token';
    }
    try {
      upload.files.add(await http.MultipartFile.fromPath('file', filePath));
    } on FileSystemException {
      throw const ApiException(
        'FILE_UNAVAILABLE',
        'The CSV file could not be read. Choose the file again.',
      );
    }
    final response = await _transport(
      () => (() async {
        _requireSession(generation);
        final streamed = await _httpClient.send(upload);
        return http.Response.fromStream(streamed);
      })().timeout(uploadTimeout),
      mutation: true,
    );
    _requireSession(generation);
    return _decode(response, mutation: true);
  }

  Future<T> _transport<T>(
    Future<T> Function() send, {
    bool retryRead = false,
    bool mutation = false,
  }) async {
    final attempts = retryRead ? 2 : 1;
    for (var attempt = 0; attempt < attempts; attempt++) {
      try {
        return await send();
      } on TimeoutException {
        // A timeout does not cancel a write already accepted by the server.
        throw ApiException(
          'REQUEST_TIMEOUT',
          mutation
              ? 'The server took too long to respond. Your change may have been '
                    'saved. Refresh and check before submitting again.'
              : 'The server took too long to respond. Please try again.',
        );
      } on SocketException {
        if (attempt + 1 == attempts) break;
      } on http.ClientException {
        if (attempt + 1 == attempts) break;
      } on HandshakeException {
        throw const ApiException(
          'SECURE_CONNECTION_FAILED',
          'A secure connection could not be established. Please try again later.',
        );
      } on FileSystemException {
        throw const ApiException(
          'FILE_UNAVAILABLE',
          'The CSV file could not be read. Choose the file again.',
        );
      }
    }
    throw ApiException(
      'NETWORK_ERROR',
      mutation
          ? 'The connection was interrupted. Your change may have been saved. '
                'Reconnect, then refresh and check before submitting again.'
          : 'Unable to connect to Spendly. Check your internet connection and try again.',
    );
  }

  Map<String, dynamic> _decode(
    http.Response response, {
    bool mutation = false,
  }) {
    if (response.statusCode >= 500) {
      throw ApiException(
        'SERVICE_UNAVAILABLE',
        mutation
            ? 'Spendly is temporarily unavailable. Your change may have been saved. '
                  'Refresh and check before submitting again.'
            : 'Spendly is temporarily unavailable. Please try again later.',
        statusCode: response.statusCode,
      );
    }
    dynamic payload;
    try {
      payload = response.body.isEmpty
          ? <String, dynamic>{}
          : jsonDecode(response.body);
    } on FormatException {
      // Gateways may return HTML. Never expose their response or request URL.
    }
    final decoded = payload is Map<String, dynamic>
        ? payload
        : <String, dynamic>{};
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final error = decoded['error'];
      final details = error is Map<String, dynamic>
          ? error
          : <String, dynamic>{};
      throw ApiException(
        details['code'] is String ? details['code'] as String : 'HTTP_ERROR',
        details['message'] is String
            ? details['message'] as String
            : response.statusCode == 401
            ? 'Your session has expired. Please sign in again.'
            : 'The request could not be completed. Please try again.',
        statusCode: response.statusCode,
      );
    }
    if (payload is! Map<String, dynamic>) {
      throw ApiException(
        'INVALID_RESPONSE',
        mutation
            ? 'Spendly returned an unexpected response. Your change may have been '
                  'saved. Refresh and check before submitting again.'
            : 'Spendly returned an unexpected response. Please try again later.',
      );
    }
    final data = decoded['data'];
    if (data is Map<String, dynamic>) return data;
    if (data is List<dynamic>) return <String, dynamic>{'items': data};
    return <String, dynamic>{};
  }

  int get sessionGeneration => _session.generation;
  int beginSessionChange() {
    if (_closed) throw StateError('API client is closed.');
    return ++_session.generation;
  }

  bool isSessionCurrent(int generation) =>
      !_closed && generation == _session.generation;

  void _requireSession(int generation) {
    if (!isSessionCurrent(generation)) {
      throw const ApiException(
        'SESSION_CHANGED',
        'Your session changed. Please sign in again.',
      );
    }
  }

  Future<String?> readToken() => _session.run(_tokenStore.read);

  Future<bool> saveSession(
    int generation,
    Map<String, dynamic> user, {
    String? token,
  }) => _session.run(() async {
    if (!isSessionCurrent(generation)) return false;
    final currentToken = token ?? await _tokenStore.read();
    if (!isSessionCurrent(generation)) return false;
    if (currentToken == null) {
      throw const ApiException('SESSION_CHANGED', 'Please sign in again.');
    }
    await _tokenStore.writeSession(currentToken, jsonEncode(user));
    return isSessionCurrent(generation);
  });
  Future<Map<String, dynamic>?> readCachedUser() async {
    final value = await _session.run(_tokenStore.readUser);
    if (value == null) return null;
    try {
      final decoded = jsonDecode(value);
      return decoded is Map<String, dynamic> ? decoded : null;
    } on FormatException {
      return null;
    }
  }

  Future<void> clearToken({int? expectedGeneration}) {
    if (expectedGeneration != null && !isSessionCurrent(expectedGeneration)) {
      return Future.value();
    }
    beginSessionChange();
    return _session.run(_tokenStore.clear);
  }

  void close() {
    _closed = true;
    _httpClient.close();
  }
}
