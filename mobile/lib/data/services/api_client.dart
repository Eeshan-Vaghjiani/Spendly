import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../../core/network/api_exception.dart';
import 'token_store.dart';

class ApiClient {
  ApiClient({
    required this.baseUrl,
    required TokenStore tokenStore,
    http.Client? httpClient,
    this.requestTimeout = const Duration(seconds: 30),
    this.uploadTimeout = const Duration(minutes: 2),
  }) : _tokenStore = tokenStore,
       _httpClient = httpClient ?? http.Client();

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
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (authenticated) {
      final token = await _tokenStore.read();
      if (token != null) {
        headers['Authorization'] = 'Bearer $token';
      }
    }
    final uri = Uri.parse('$baseUrl$path');
    Future<http.Response> send() {
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
    return _decode(response, mutation: method != 'GET');
  }

  Future<Map<String, dynamic>> uploadCsv(String filePath) async {
    final upload = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/transactions/upload'),
    );
    final token = await _tokenStore.read();
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
        final streamed = await _httpClient.send(upload);
        return http.Response.fromStream(streamed);
      })().timeout(uploadTimeout),
      mutation: true,
    );
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

  Future<void> saveToken(String token) => _tokenStore.write(token);
  Future<String?> readToken() => _tokenStore.read();
  Future<void> saveCachedUser(Map<String, dynamic> user) =>
      _tokenStore.writeUser(jsonEncode(user));
  Future<Map<String, dynamic>?> readCachedUser() async {
    final value = await _tokenStore.readUser();
    if (value == null) return null;
    try {
      return jsonDecode(value) as Map<String, dynamic>;
    } on FormatException {
      return null;
    }
  }

  Future<void> clearToken() => _tokenStore.clear();
}
