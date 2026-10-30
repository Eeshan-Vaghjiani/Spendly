import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/core/theme/app_theme.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/mpesa_settings_screen.dart';
import 'package:spending_support/presentation/screens/privacy_info_screen.dart';
import 'package:spending_support/presentation/screens/profile_screen.dart';
import 'package:spending_support/presentation/screens/transaction_history_screen.dart';

import 'mpesa_consent_test.dart' show SmsFixturePlatform, SmsFixtureRepository;
import 'widget_test.dart' show FakeGoogleIdentity;

class _SettingsRepository extends SmsFixtureRepository {
  int trainingUpdates = 0;

  @override
  Future<UserProfile> updateConsent({
    required bool acceptedTerms,
    required bool acceptedPrivacy,
    required bool modelTrainingOptIn,
  }) async {
    trainingUpdates++;
    return UserProfile(
      id: 'alpha',
      email: 'alpha@example.invalid',
      displayName: 'Alpha',
      modelTrainingOptIn: modelTrainingOptIn,
    );
  }
}

Future<void> _show(
  WidgetTester tester,
  Widget page,
  _SettingsRepository repository,
  SmsFixturePlatform platform, {
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
        mpesaPlatformProvider.overrideWithValue(platform),
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

Future<void> _search(WidgetTester tester, String query) async {
  await tester.enterText(find.byKey(const Key('settings-search')), query);
  await tester.pumpAndSettle();
}

void main() {
  late _SettingsRepository repository;
  late SmsFixturePlatform platform;
  setUp(() {
    repository = _SettingsRepository();
    platform = SmsFixturePlatform();
  });

  testWidgets('search aliases are local and never enable or sync SMS', (
    tester,
  ) async {
    await _show(tester, const ProfileScreen(), repository, platform);
    for (final query in ['SMS', ' mpesa ', 'M-PESA', 'sync', 'import']) {
      await _search(tester, query);
      expect(find.byKey(const Key('open-mpesa-import')), findsOneWidget);
      expect(find.text('Imports and sync'), findsOneWidget);
      expect(find.byKey(const Key('edit-username')), findsNothing);
      expect(platform.calls, isEmpty);
      expect(repository.calls, isEmpty);
      expect(repository.trainingUpdates, 0);
    }
  });

  testWidgets('search results open existing SMS settings without enabling', (
    tester,
  ) async {
    await _show(tester, const ProfileScreen(), repository, platform);
    await _search(tester, 'SMS');
    await tester.tap(find.byKey(const Key('open-mpesa-import')));
    await tester.pumpAndSettle();
    expect(find.byType(MpesaSettingsScreen), findsOneWidget);
    expect(find.text('Off'), findsOneWidget);
    expect(platform.calls, isEmpty);
    expect(repository.calls, isEmpty);
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<TextField>(find.byKey(const Key('settings-search')))
          .controller!
          .text,
      'SMS',
    );
  });

  testWidgets('privacy result opens directly without resubmitting consent', (
    tester,
  ) async {
    await _show(tester, const ProfileScreen(), repository, platform);
    await _search(tester, 'privacy');
    await tester.tap(find.byKey(const Key('view-privacy-summary')));
    await tester.pumpAndSettle();
    expect(find.byType(PrivacyInfoScreen), findsOneWidget);
    expect(repository.trainingUpdates, 0);
    expect(platform.calls, isEmpty);
  });

  testWidgets('search preserves an already enabled importer and its status', (
    tester,
  ) async {
    repository.enabled = true;
    platform.enabled = true;
    platform.allowed = true;
    await _show(tester, const ProfileScreen(), repository, platform);
    await _search(tester, 'sync');
    expect(platform.calls, isEmpty);
    await tester.tap(find.byKey(const Key('open-mpesa-import')));
    await tester.pumpAndSettle();
    expect(find.text('Active'), findsOneWidget);
    expect(platform.enabled, isTrue);
    expect(platform.allowed, isTrue);
    expect(platform.calls, isEmpty);
    expect(repository.calls, isEmpty);
  });

  testWidgets(
    'no results and clear search do not index personal profile values',
    (tester) async {
      await _show(tester, const ProfileScreen(), repository, platform);
      await _search(tester, 'alpha@example.invalid');
      expect(
        find.text('No settings found. Try SMS, privacy or account.'),
        findsOneWidget,
      );
      await tester.tap(find.byTooltip('Clear settings search'));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('edit-username')), findsOneWidget);
      expect(
        tester
            .widget<TextField>(find.byKey(const Key('settings-search')))
            .controller!
            .text,
        isEmpty,
      );
    },
  );

  testWidgets(
    'training choice survives filtering and still requires an explicit change',
    (tester) async {
      await _show(tester, const ProfileScreen(), repository, platform);
      await _search(tester, 'training');
      final choice = find.byKey(const Key('model-training-choice'));
      expect(tester.widget<SwitchListTile>(choice).value, isFalse);
      expect(repository.trainingUpdates, 0);
      await tester.tap(choice);
      await tester.pumpAndSettle();
      expect(repository.trainingUpdates, 1);
      await _search(tester, 'SMS');
      await _search(tester, 'training');
      expect(tester.widget<SwitchListTile>(choice).value, isTrue);
      expect(repository.trainingUpdates, 1);
      expect(platform.calls, isEmpty);
    },
  );

  testWidgets('transactions open sync directly and reload on return', (
    tester,
  ) async {
    await _show(tester, const TransactionHistoryScreen(), repository, platform);
    final before = repository.transactionListCalls;
    await tester.tap(find.byTooltip('M-PESA sync'));
    await tester.pumpAndSettle();
    expect(find.byType(MpesaSettingsScreen), findsOneWidget);
    expect(platform.calls, isEmpty);
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(repository.transactionListCalls, before + 1);
    expect(tester.takeException(), isNull);
  });

  testWidgets('search, clear and sections fit narrow 200 percent text', (
    tester,
  ) async {
    await _show(tester, const ProfileScreen(), repository, platform, scale: 2);
    await _search(tester, 'training');
    await tester.ensureVisible(find.byKey(const Key('model-training-choice')));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    await _search(tester, 'not-a-setting');
    tester.view.viewInsets = const FakeViewPadding(bottom: 280);
    addTearDown(tester.view.resetViewInsets);
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    await tester.tap(find.byTooltip('Clear settings search'));
    tester.view.resetViewInsets();
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Sign out'),
      200,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });
}
