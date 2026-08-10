import 'package:flutter_secure_storage/flutter_secure_storage.dart';

abstract class TokenStore {
  Future<void> write(String token);
  Future<String?> read();
  Future<void> writeUser(String userJson);
  Future<String?> readUser();
  Future<void> clear();
}

class SecureTokenStore implements TokenStore {
  SecureTokenStore({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  static const _key = 'access_token';
  static const _userKey = 'signed_in_user';
  final FlutterSecureStorage _storage;

  @override
  Future<void> write(String token) => _storage.write(key: _key, value: token);

  @override
  Future<String?> read() => _storage.read(key: _key);

  @override
  Future<void> writeUser(String userJson) =>
      _storage.write(key: _userKey, value: userJson);

  @override
  Future<String?> readUser() => _storage.read(key: _userKey);

  @override
  Future<void> clear() async {
    await _storage.delete(key: _key);
    await _storage.delete(key: _userKey);
  }
}
