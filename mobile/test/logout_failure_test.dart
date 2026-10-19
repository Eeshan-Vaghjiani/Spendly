import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/profile_screen.dart';

import 'widget_test.dart' show FakeGoogleIdentity, FakeRepository;

class FailingGoogleSignOut extends FakeGoogleIdentity {
  @override
  Future<void> signOut() async => throw Exception('Synthetic provider failure');
}

class LogoutRepository extends FakeRepository {
  LogoutRepository()
    : super(
        restoredUser: const UserProfile(
          id: 'synthetic-account',
          email: 'synthetic@example.com',
          displayName: 'Synthetic',
        ),
      );

  int logoutCalls = 0;
  bool storageFails = false;

  @override
  Future<void> logout() async {
    logoutCalls++;
    if (storageFails) throw Exception('Synthetic storage failure');
  }
}

void main() {
  testWidgets(
    'storage failure keeps account visible and offers sign-out retry',
    (tester) async {
      final repository = LogoutRepository()..storageFails = true;
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            repositoryProvider.overrideWithValue(repository),
            googleIdentityProvider.overrideWithValue(FakeGoogleIdentity()),
          ],
          child: const MaterialApp(home: ProfileScreen()),
        ),
      );
      await tester.pumpAndSettle();
      final container = ProviderScope.containerOf(
        tester.element(find.byType(ProfileScreen)),
      );
      await tester.scrollUntilVisible(find.text('Sign out'), 250);
      await tester.tap(find.text('Sign out'));
      await tester.pumpAndSettle();
      expect(
        find.text('Could not sign out. Please try again.'),
        findsOneWidget,
      );
      expect(container.read(authControllerProvider).user, isNotNull);
      expect(repository.logoutCalls, 1);
      expect(tester.takeException(), isNull);
      repository.storageFails = false;
      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Sign out'));
      await tester.pumpAndSettle();
      expect(container.read(authControllerProvider).user, isNull);
      expect(repository.logoutCalls, 2);
    },
  );

  test(
    'Google sign-out failure still clears local auth and cached insights',
    () async {
      final repository = LogoutRepository();
      final container = ProviderContainer(
        overrides: [
          repositoryProvider.overrideWithValue(repository),
          googleIdentityProvider.overrideWithValue(FailingGoogleSignOut()),
        ],
      );
      addTearDown(container.dispose);
      final auth = container.read(authControllerProvider.notifier);
      await Future<void>.delayed(Duration.zero);
      expect(container.read(authControllerProvider).user, isNotNull);
      final subscription = container.listen(
        analysisControllerProvider,
        (_, _) {},
      );
      addTearDown(subscription.close);
      await container.read(analysisControllerProvider.notifier).loadLatest();
      expect(container.read(analysisControllerProvider).result, isNotNull);

      await auth.logout();

      expect(repository.logoutCalls, 1);
      expect(container.read(authControllerProvider).user, isNull);
      expect(container.read(analysisControllerProvider).result, isNull);
      expect(container.read(analysisControllerProvider).error, isNull);
      expect(container.read(analysisControllerProvider).loading, isFalse);
    },
  );
}
