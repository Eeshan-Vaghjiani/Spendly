import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/core/theme/app_theme.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/consent_setup_screen.dart';
import 'package:spending_support/presentation/screens/privacy_info_screen.dart';
import 'package:spending_support/presentation/screens/profile_screen.dart';

import 'widget_test.dart' show FakeGoogleIdentity, FakeRepository;

const _user = UserProfile(
  id: 'synthetic-privacy',
  email: 'privacy@example.invalid',
  displayName: 'Privacy test',
  modelTrainingOptIn: true,
);

class _PrivacyRepository extends FakeRepository {
  _PrivacyRepository() : super(restoredUser: _user);
  int consentUpdates = 0;

  @override
  Future<UserProfile> updateConsent({
    required bool acceptedTerms,
    required bool acceptedPrivacy,
    required bool modelTrainingOptIn,
  }) async {
    consentUpdates++;
    return _user;
  }
}

Future<void> _show(
  WidgetTester tester,
  Widget page,
  _PrivacyRepository repository, {
  double scale = 1,
}) async {
  tester.view.physicalSize = const Size(320, 640);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        repositoryProvider.overrideWithValue(repository),
        googleIdentityProvider.overrideWithValue(FakeGoogleIdentity()),
      ],
      child: MaterialApp(
        theme: AppTheme.light(),
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(
            context,
          ).copyWith(textScaler: TextScaler.linear(scale)),
          child: child!,
        ),
        home: page,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  for (final scale in [1.0, 2.0]) {
    for (final setup in [false, true]) {
      testWidgets(
        '${setup ? 'setup' : 'read-only'} privacy summary fits at ${scale * 100} percent',
        (tester) async {
          final repository = _PrivacyRepository();
          await _show(
            tester,
            setup ? const ConsentSetupScreen() : const PrivacyInfoScreen(),
            repository,
            scale: scale,
          );
          await tester.scrollUntilVisible(find.text('Who can see it'), 200);
          await tester.pumpAndSettle();
          expect(
            find.textContaining('Authorized administrators'),
            findsOneWidget,
          );
          expect(
            find.textContaining('successful changes are audited'),
            findsOneWidget,
          );
          expect(find.textContaining('sign-in method'), findsOneWidget);
          expect(
            find.textContaining('track your device or location'),
            findsOneWidget,
          );
          expect(
            find.textContaining('not automatically used for training'),
            findsOneWidget,
          );
          final scroll = tester.state<ScrollableState>(
            find.byType(Scrollable).first,
          );
          while (scroll.position.extentAfter > 0) {
            scroll.position.jumpTo(
              (scroll.position.pixels + 400).clamp(
                0,
                scroll.position.maxScrollExtent,
              ),
            );
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
          }
          expect(repository.consentUpdates, 0);
          if (setup) {
            final button = tester.widget<FilledButton>(
              find.byKey(const Key('complete-data-setup')),
            );
            expect(button.onPressed, isNull);
          } else {
            expect(find.byType(CheckboxListTile), findsNothing);
            expect(find.byType(SwitchListTile), findsNothing);
          }
        },
      );
    }
  }

  testWidgets('Profile opens the summary without resubmitting consent', (
    tester,
  ) async {
    final repository = _PrivacyRepository();
    await _show(tester, const ProfileScreen(), repository);
    await tester.scrollUntilVisible(
      find.byKey(const Key('view-privacy-summary')),
      200,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('view-privacy-summary')));
    await tester.pumpAndSettle();
    expect(find.byType(PrivacyInfoScreen), findsOneWidget);
    expect(find.text('Summary updated 22 October 2026'), findsOneWidget);
    expect(repository.consentUpdates, 0);
  });
}
