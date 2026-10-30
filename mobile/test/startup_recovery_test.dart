import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/main.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/home_shell.dart';
import 'widget_test.dart' show FakeRepository, FakeGoogleIdentity;

const user = UserProfile(
  id: 'synthetic-startup',
  email: 'startup@example.invalid',
  displayName: 'Startup',
);

class StartupRepository extends FakeRepository {
  bool fails = true;
  Completer<UserProfile?>? pending;
  @override
  Future<UserProfile?> restoreSession() async {
    if (pending != null) return pending!.future;
    if (fails) {
      throw PlatformException(
        code: 'fixture-read',
        message: 'private storage diagnostic',
      );
    }
    return user;
  }
}

void main() {
  testWidgets(
    'startup storage failure gives a safe retry and recovers without clearing credentials',
    (tester) async {
      final repository = StartupRepository();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            repositoryProvider.overrideWithValue(repository),
            googleIdentityProvider.overrideWithValue(FakeGoogleIdentity()),
          ],
          child: const SpendlyApp(),
        ),
      );
      await tester.pumpAndSettle();
      expect(
        find.text('Could not open your saved session. Please try again.'),
        findsOneWidget,
      );
      expect(find.textContaining('private storage diagnostic'), findsNothing);
      expect(find.text('Retry'), findsOneWidget);
      repository.fails = false;
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();
      expect(find.byType(HomeShell), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
  for (final fails in [false, true]) {
    test(
      'late startup ${fails ? 'failure' : 'success'} after disposal is ignored',
      () async {
        final repository = StartupRepository()
          ..pending = Completer<UserProfile?>();
        final auth = AuthController(repository, FakeGoogleIdentity());
        auth.dispose();
        if (fails) {
          repository.pending!.completeError(
            StateError('Synthetic old restore'),
          );
        } else {
          repository.pending!.complete(user);
        }
        await Future<void>.delayed(Duration.zero);
      },
    );
  }
}
