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
  }) : _tokenStore = tokenStore,
       _httpClient = httpClient ?? http.Client();

  final String baseUrl;
  final TokenStore _tokenStore;
  final http.Client _httpClient;

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

    try {
      return _decode(await send());
    } on SocketException {
      if (!retryOnce) rethrow;
      return _decode(await send());
    } on http.ClientException {
      if (!retryOnce) rethrow;
      return _decode(await send());
    }
  }

  Future<Map<String, dynamic>> uploadCsv(String filePath) async {
    final request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/transactions/upload'),
    );
    final token = await _tokenStore.read();
    if (token != null) {
      request.headers['Authorization'] = 'Bearer $token';
    }
    request.files.add(await http.MultipartFile.fromPath('file', filePath));
    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);
    return _decode(response);
  }

  Map<String, dynamic> _decode(http.Response response) {
    final decoded = response.body.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode < 200 || response.statusCode >= 300) {
      final error =
          decoded['error'] as Map<String, dynamic>? ??
          const <String, dynamic>{};
      throw ApiException(
        error['code'] as String? ?? 'HTTP_ERROR',
        error['message'] as String? ?? 'The request could not be completed.',
        statusCode: response.statusCode,
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
