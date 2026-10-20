import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

abstract class TokenStore {
  Future<void> writeSession(String token, String userJson);
  Future<String?> read();
  Future<String?> readUser();
  Future<void> clear();
}

class SecureTokenStore implements TokenStore {
  SecureTokenStore({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  static const _key = 'access_token';
  static const _userKey = 'signed_in_user';
  static const _sessionKey = 'signed_in_session_v2';
  // All production wrappers use these same secure-storage keys.
  static final Object sessionScope = Object();
  final FlutterSecureStorage _storage;

  @override
  Future<void> writeSession(String token, String userJson) async {
    await _storage.write(
      key: _sessionKey,
      value: jsonEncode({'token': token, 'user_json': userJson}),
    );
    await _removeLegacyKeys();
  }

  @override
  Future<String?> read() async => (await _readSession())?['token'];

  Future<Map<String, String>?> _readSession() async {
    final value = await _storage.read(key: _sessionKey);
    if (value != null) {
      try {
        final decoded = jsonDecode(value);
        if (decoded is Map &&
            decoded['token'] is String &&
            decoded['user_json'] is String) {
          return {
            'token': decoded['token'] as String,
            'user_json': decoded['user_json'] as String,
          };
        }
      } on FormatException {
        // A present versioned record never falls back to obsolete credentials.
      }
      return null;
    }
    final token = await _storage.read(key: _key);
    final user = await _storage.read(key: _userKey);
    return token == null || user == null
        ? null
        : {'token': token, 'user_json': user};
  }

  @override
  Future<String?> readUser() async => (await _readSession())?['user_json'];

  @override
  Future<void> clear() async {
    // Keep a durable signed-out record: legacy keys must not resurrect a session
    // if cleanup is interrupted or a platform deletion fails.
    await _storage.write(key: _sessionKey, value: '{"signed_out":true}');
    await _removeLegacyKeys();
  }

  Future<void> _removeLegacyKeys() async {
    for (final key in [_key, _userKey]) {
      try {
        await _storage.delete(key: key);
      } catch (_) {
        // The complete versioned record is already authoritative. Never log
        // credential values; obsolete keys can be removed on the next write.
      }
    }
  }
}
