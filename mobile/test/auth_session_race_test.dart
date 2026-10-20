import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/data/repositories/api_spending_repository.dart';
import 'package:spending_support/data/services/api_client.dart';
import 'package:spending_support/presentation/controllers/providers.dart';

import 'api_client_test.dart' show MemoryTokenStore;
import 'widget_test.dart' show FakeGoogleIdentity, FakeRepository;

const alpha = UserProfile(
  id: 'synthetic-alpha',
  email: 'alpha@example.invalid',
  displayName: 'Alpha',
);
const beta = UserProfile(
  id: 'synthetic-beta',
  email: 'beta@example.invalid',
  displayName: 'Beta',
);
Map<String, dynamic> profile(UserProfile user) => {
  'id': user.id,
  'email': user.email,
  'display_name': user.displayName,
  'has_required_consents': true,
};
http.Response response(Map<String, dynamic> data) =>
    http.Response(jsonEncode({'success': true, 'data': data}), 200);

class DelayedAccountRepository extends FakeRepository {
  DelayedAccountRepository() : super(restoredUser: alpha);
  final pending = Completer<UserProfile>();
  Completer<void>? logoutGate;
  int logoutCalls = 0;
  bool delayLogin = false;
  @override
  Future<UserProfile> updateConsent({
    required bool acceptedTerms,
    required bool acceptedPrivacy,
    required bool modelTrainingOptIn,
  }) => pending.future;
  @override
  Future<UserProfile> updateUsername(String username) => pending.future;
  @override
  Future<UserProfile> completeOnboarding({required bool skipped}) =>
      pending.future;
  @override
  Future<UserProfile> login(String email, String password) =>
      delayLogin ? pending.future : Future.value(beta);
  @override
  Future<void> logout() async {
    logoutCalls++;
    await logoutGate?.future;
  }
}

class PendingGoogleIdentity extends FakeGoogleIdentity {
  PendingGoogleIdentity() : super(configured: true);
  final identity = Completer<String>();
  final cleanup = Completer<void>();
  bool delayIdentity = false;
  @override
  Future<String> authenticate() =>
      delayIdentity ? identity.future : Future.value('synthetic-id');
  @override
  Future<void> signOut() => cleanup.future;
}

Future<bool> change(AuthController auth, String operation) =>
    switch (operation) {
      'consent' => auth.updateConsent(modelTrainingOptIn: true),
      'username' => auth.updateUsername('synthetic_updated'),
      _ => auth.completeOnboarding(skipped: false),
    };

void main() {
  test(
    'unexpected account errors keep the current user and hide diagnostics',
    () async {
      final repository = DelayedAccountRepository();
      final auth = AuthController(repository, FakeGoogleIdentity());
      addTearDown(auth.dispose);
      await Future<void>.delayed(Duration.zero);
      final request = auth.updateConsent(modelTrainingOptIn: true);
      repository.pending.completeError(Exception('private fixture diagnostic'));
      expect(await request, false);
      expect(auth.state.user?.id, alpha.id);
      expect(auth.state.error, isNot(contains('private fixture')));
      expect(auth.state.loading, false);
    },
  );
  test(
    'hung Google cleanup releases email signin without starting another Google flow',
    () async {
      final repository = DelayedAccountRepository();
      final identity = PendingGoogleIdentity();
      final auth = AuthController(
        repository,
        identity,
        googleCleanupTimeout: const Duration(milliseconds: 10),
      );
      addTearDown(auth.dispose);
      await Future<void>.delayed(Duration.zero);
      await auth.logout();
      expect(auth.state.user, isNull);
      expect(auth.state.loading, false);
      expect(await auth.loginWithGoogle(), false);
      expect(await auth.login(beta.email, 'synthetic-only'), true);
      identity.cleanup.complete();
      await Future<void>.delayed(Duration.zero);
      expect(auth.state.user?.id, beta.id);
    },
  );

  test(
    'Google identity returning after logout does not exchange or restore a session',
    () async {
      final repository = DelayedAccountRepository();
      final identity = PendingGoogleIdentity()..delayIdentity = true;
      identity.cleanup.complete();
      final auth = AuthController(repository, identity);
      addTearDown(auth.dispose);
      await Future<void>.delayed(Duration.zero);
      final signin = auth.loginWithGoogle();
      await auth.logout();
      identity.identity.complete('synthetic-late-id');
      expect(await signin, false);
      expect(auth.state.user, isNull);
    },
  );
  for (final operation in ['consent', 'username', 'onboarding']) {
    for (final boundary in ['logout', 'switch', 'dispose']) {
      for (final fails in [false, true]) {
        test(
          '$operation late ${fails ? 'failure' : 'success'} cannot cross $boundary',
          () async {
            final repository = DelayedAccountRepository();
            final auth = AuthController(repository, FakeGoogleIdentity());
            await Future<void>.delayed(Duration.zero);
            final request = change(auth, operation);
            if (boundary == 'dispose') {
              auth.dispose();
            } else {
              addTearDown(auth.dispose);
              await auth.logout();
              if (boundary == 'switch') {
                expect(await auth.login(beta.email, 'synthetic-only'), true);
              }
            }
            if (fails) {
              repository.pending.completeError(
                Exception('Old account request failed'),
              );
            } else {
              repository.pending.complete(alpha);
            }
            expect(await request, false);
            if (boundary != 'dispose') {
              expect(
                auth.state.user?.id,
                boundary == 'switch' ? beta.id : null,
              );
              expect(auth.state.error, isNull);
            }
          },
        );
      }
    }
  }

  test(
    'duplicate logout calls share cleanup and signin waits for it',
    () async {
      final repository = DelayedAccountRepository()
        ..logoutGate = Completer<void>();
      final auth = AuthController(repository, FakeGoogleIdentity());
      addTearDown(auth.dispose);
      await Future<void>.delayed(Duration.zero);
      final first = auth.logout(), second = auth.logout();
      expect(repository.logoutCalls, 1);
      expect(await auth.login(beta.email, 'synthetic-only'), false);
      repository.logoutGate!.complete();
      await Future.wait([first, second]);
      expect(auth.state.user, isNull);
      expect(auth.state.loading, false);
    },
  );

  for (final operation in ['profile', 'renew', 'login']) {
    test(
      'late $operation response cannot overwrite a newer stored account',
      () async {
        final store = MemoryTokenStore()
          ..token = 'synthetic-alpha-token'
          ..userJson = jsonEncode(profile(alpha));
        final pending = Completer<http.Response>(), started = Completer<void>();
        final repository = ApiSpendingRepository(
          ApiClient(
            baseUrl: 'http://localhost/api/v1',
            tokenStore: store,
            httpClient: MockClient((request) {
              if ((operation == 'profile' &&
                      request.url.path.endsWith('/auth/profile')) ||
                  (operation == 'renew' &&
                      request.url.path.endsWith('/auth/renew')) ||
                  (operation == 'login' &&
                      request.body.contains('alpha@example.invalid'))) {
                if (!started.isCompleted) started.complete();
                return pending.future;
              }
              return Future.value(
                response({
                  'access_token': 'synthetic-beta-token',
                  'user': profile(beta),
                }),
              );
            }),
          ),
        );
        final old = operation == 'profile'
            ? repository.updateUsername('alpha_changed')
            : operation == 'renew'
            ? repository.restoreSession()
            : repository.login(alpha.email, 'synthetic-only');
        final observed = old.then<Object?>(
          (value) => value,
          onError: (Object error) => error,
        );
        await started.future;
        await repository.logout();
        await repository.login(beta.email, 'synthetic-only');
        pending.complete(
          response(
            operation == 'profile'
                ? profile(alpha)
                : {
                    'access_token': 'synthetic-old-token',
                    'user': profile(alpha),
                  },
          ),
        );
        await observed;
        expect(store.token, 'synthetic-beta-token');
        expect(jsonDecode(store.userJson!)['id'], beta.id);
      },
    );
  }

  test('old renewal 401 cannot clear the newer stored account', () async {
    final store = MemoryTokenStore()
      ..token = 'synthetic-alpha-token'
      ..userJson = jsonEncode(profile(alpha));
    final pending = Completer<http.Response>(), started = Completer<void>();
    final repository = ApiSpendingRepository(
      ApiClient(
        baseUrl: 'http://localhost/api/v1',
        tokenStore: store,
        httpClient: MockClient((request) {
          if (request.url.path.endsWith('/auth/renew')) {
            started.complete();
            return pending.future;
          }
          return Future.value(
            response({
              'access_token': 'synthetic-beta-token',
              'user': profile(beta),
            }),
          );
        }),
      ),
    );
    final old = repository.restoreSession();
    await started.future;
    await repository.logout();
    await repository.login(beta.email, 'synthetic-only');
    pending.complete(
      http.Response(
        '{"error":{"code":"TOKEN_EXPIRED","message":"Expired"}}',
        401,
      ),
    );
    expect(await old, isNull);
    expect(store.token, 'synthetic-beta-token');
    expect(jsonDecode(store.userJson!)['id'], beta.id);
  });
}
