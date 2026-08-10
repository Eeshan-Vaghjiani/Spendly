import 'package:google_sign_in/google_sign_in.dart';

import '../../core/config/app_config.dart';

abstract class GoogleIdentityProvider {
  bool get isConfigured;
  Future<String> authenticate();
  Future<void> signOut();
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
    await _initialize();
    if (!_googleSignIn.supportsAuthenticate()) {
      throw UnsupportedError('Google sign-in is unavailable on this device.');
    }
    final account = await _googleSignIn.authenticate();
    final token = account.authentication.idToken;
    if (token == null || token.isEmpty) {
      throw StateError('Google did not return an identity token.');
    }
    return token;
  }

  @override
  Future<void> signOut() async {
    if (_initialization == null) return;
    await _googleSignIn.signOut();
  }
}
