import 'dart:async';

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
  static final _signOuts = Expando<Future<void>>();
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
      final cleanup = _signOuts[_googleSignIn];
      if (cleanup != null) {
        try {
          await cleanup
              .catchError((Object _) {})
              .timeout(const Duration(seconds: 5));
        } on TimeoutException {
          throw const GoogleIdentityException(
            'Google sign-out is still finishing. Try again or sign in with email.',
          );
        }
      }
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
  Future<void> signOut() {
    final pending = _signOuts[_googleSignIn];
    if (pending != null) return pending;
    if (_initialization == null) return Future.value();
    late final Future<void> cleanup;
    cleanup = Future<void>.sync(_googleSignIn.signOut).whenComplete(() {
      if (identical(_signOuts[_googleSignIn], cleanup)) {
        _signOuts[_googleSignIn] = null;
      }
    });
    _signOuts[_googleSignIn] = cleanup;
    return cleanup;
  }
}
