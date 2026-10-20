import 'dart:async';
import 'package:flutter_test/flutter_test.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:spending_support/data/services/google_identity_service.dart';

class FixtureGoogleSdk implements GoogleSignIn {
  final cleanup = Completer<void>();
  int authenticateCalls = 0, signOutCalls = 0;
  @override
  Future<void> initialize({
    String? clientId,
    String? serverClientId,
    String? nonce,
    String? hostedDomain,
  }) async {}
  @override
  bool supportsAuthenticate() => true;
  @override
  Future<GoogleSignInAccount> authenticate({
    List<String> scopeHint = const [],
  }) async {
    authenticateCalls++;
    throw StateError('Synthetic SDK identity not provided');
  }

  @override
  Future<void> signOut() {
    signOutCalls++;
    return cleanup.future;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class ConfiguredIdentity extends GoogleIdentityService {
  ConfiguredIdentity(FixtureGoogleSdk sdk) : super(googleSignIn: sdk);
  @override
  bool get isConfigured => true;
}

void main() {
  test(
    'new service wrapper waits for shared SDK cleanup and coalesces signout',
    () async {
      final sdk = FixtureGoogleSdk();
      final first = ConfiguredIdentity(sdk);
      await expectLater(
        first.authenticate(),
        throwsA(isA<GoogleIdentityException>()),
      );
      expect(sdk.authenticateCalls, 1);
      final cleanup = first.signOut();
      final second = ConfiguredIdentity(sdk);
      final secondCleanup = second.signOut();
      final signin = second.authenticate();
      final observed = expectLater(
        signin,
        throwsA(isA<GoogleIdentityException>()),
      );
      await Future<void>.delayed(Duration.zero);
      expect(sdk.signOutCalls, 1);
      expect(sdk.authenticateCalls, 1);
      sdk.cleanup.complete();
      await Future.wait([cleanup, secondCleanup, observed]);
      expect(sdk.authenticateCalls, 2);
    },
  );
}
