import 'package:google_sign_in/google_sign_in.dart';

import '../../core/config/app_config.dart';

abstract class GoogleIdentityProvider {
  bool get isConfigured;
  Future<String> authenticate();
  Future<void> signOut();
}

class GoogleIdentityException implements Exception {
  const GoogleIdentityException(this.message);

  final String message;

  @override
  String toString() => message;
}

class GoogleIdentityService implements GoogleIdentityProvider {
  GoogleIdentityService({GoogleSignIn? googleSignIn})
    : _googleSignIn = googleSignIn ?? GoogleSignIn.instance;

  final GoogleSignIn _googleSignIn;
  Future<void>? _initialization;

  @override
  bool get isConfigured => AppConfig.googleWebClientId.isNotEmpty;

  Future<void> _initialize() {
    if (!isConfigured) {
      throw StateError('Google sign-in is not configured in this build.');
    }
    return _initialization ??= _googleSignIn.initialize(
      serverClientId: AppConfig.googleWebClientId,
    );
  }

  @override
  Future<String> authenticate() async {
    try {
      await _initialize();
      if (!_googleSignIn.supportsAuthenticate()) {
        throw const GoogleIdentityException(
          'Google sign-in is unavailable on this device.',
        );
      }
      final account = await _googleSignIn.authenticate();
      final token = account.authentication.idToken;
      if (token == null || token.isEmpty) {
        throw const GoogleIdentityException(
          'Google did not return an identity token. Please try again.',
        );
      }
      return token;
    } on GoogleSignInException catch (error) {
      final code = error.code.name;
      if (code == 'canceled' || code == 'interrupted') {
        throw const GoogleIdentityException('Google sign-in was cancelled.');
      }
      if (code == 'clientConfigurationError' ||
          code == 'providerConfigurationError') {
        throw const GoogleIdentityException(
          'Google sign-in is not configured correctly for this build.',
        );
      }
      if (code == 'uiUnavailable') {
        throw const GoogleIdentityException(
          'Google sign-in is unavailable on this device.',
        );
      }
      throw const GoogleIdentityException(
        'Google could not complete sign-in. Please try again.',
      );
    } on GoogleIdentityException {
      rethrow;
    } catch (_) {
      throw const GoogleIdentityException(
        'Could not connect to Google. Check your connection and try again.',
      );
    }
  }

  @override
  Future<void> signOut() async {
    if (_initialization == null) return;
    await _googleSignIn.signOut();
  }
}
