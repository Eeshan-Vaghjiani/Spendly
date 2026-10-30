import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/core/theme/app_theme.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/data/services/mpesa_platform.dart';
import 'package:spending_support/presentation/controllers/mpesa_controller.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/mpesa_settings_screen.dart';
import 'widget_test.dart' show FakeRepository, FakeGoogleIdentity;

class SmsFixtureRepository extends FakeRepository {
  SmsFixtureRepository()
    : super(
        restoredUser: const UserProfile(
          id: 'alpha',
          email: 'alpha@example.invalid',
          displayName: 'Alpha',
        ),
      );
  final List<String> calls = [];
  bool enabled = false, failConsent = false;
  Completer<SmsConsent>? pending;
  @override
  Future<SmsConsent> smsConsent() async => SmsConsent(
    accountId: 'alpha',
    available: true,
    enabled: enabled,
    version: enabled ? '2026-10-22' : null,
  );
  @override
  Future<SmsConsent> updateSmsConsent({
    required bool enabled,
    bool disclosureAccepted = false,
    String? version,
  }) async {
    calls.add('consent:$enabled:$disclosureAccepted');
    if (pending != null) return pending!.future;
    if (failConsent) throw StateError('private diagnostic');
    this.enabled = enabled;
    return smsConsent();
  }
}

class SmsFixturePlatform extends NoSmsPlatform {
  final List<String> calls = [];
  bool enabled = false, allowed = false, grant = false, failDisable = false;
  String? localError;
  Completer<SmsImportStatus>? pendingSync;
  @override
  Future<SmsImportStatus> status() async => SmsImportStatus(
    available: true,
    enabled: enabled,
    permission: allowed,
    active: enabled && allowed,
    error: localError,
  );
  @override
  Future<void> enable({
    required String accountId,
    required String token,
    required String baseUrl,
    required String version,
  }) async {
    calls.add('enable:$accountId');
    enabled = true;
  }

  @override
  Future<bool> requestPermission(String acceptedVersion) async {
    calls.add('permission');
    allowed = grant;
    return allowed;
  }

  @override
  Future<void> disable() async {
    calls.add('disable');
    if (failDisable) throw StateError('fixture storage failure');
    enabled = false;
    localError = null;
  }

  @override
  Future<void> historical(int days) async {
    calls.add('history:$days');
  }

  @override
  Future<SmsImportStatus> sync() async {
    calls.add('sync');
    return pendingSync?.future ??
        SmsImportStatus(
          available: true,
          enabled: true,
          permission: true,
          active: true,
          summary: const {
            'checked': 3,
            'valid': 2,
            'created': 2,
            'duplicate': 1,
            'unsupported': 1,
          },
        );
  }
}

Future<void> settle() => Future<void>.delayed(Duration.zero);

void main() {
  late SmsFixtureRepository repo;
  late SmsFixturePlatform platform;
  late String identity;
  late MpesaController controller;
  late int refreshes;
  setUp(() async {
    repo = SmsFixtureRepository();
    platform = SmsFixturePlatform();
    identity = 'alpha';
    refreshes = 0;
    controller = MpesaController(
      repo,
      platform,
      identity,
      () => identity,
      () => true,
      () async => 'synthetic-token-not-for-network',
      () => refreshes++,
    );
    await settle();
  });
  tearDown(() {
    if (controller.mounted) controller.dispose();
  });

  test(
    'default off, sync/history/permission never requested without consent',
    () async {
      expect(controller.state.status.enabled, false);
      await controller.sync(historyDays: 0);
      await controller.enable(disclosureAccepted: false);
      expect(platform.calls, isEmpty);
      expect(repo.calls, isEmpty);
    },
  );
  test(
    'backend consent precedes native enable and contextual permission; denial inactive',
    () async {
      await controller.enable(disclosureAccepted: true);
      expect(repo.calls, ['consent:true:true']);
      expect(platform.calls, ['enable:alpha', 'permission']);
      expect(controller.state.status.enabled, true);
      expect(controller.state.status.active, false);
      expect(controller.state.message, contains('Permission required'));
      await controller.sync();
      expect(platform.calls, isNot(contains('sync')));
    },
  );
  test(
    'failed consent never requests OS permission or enables local access',
    () async {
      repo.failConsent = true;
      await controller.enable(disclosureAccepted: true);
      expect(platform.calls, ['disable']);
      expect(controller.state.status.enabled, false);
      expect(controller.state.message, isNot(contains('private diagnostic')));
    },
  );
  test(
    'permission and consent are separate gates, including revocation',
    () async {
      platform.grant = true;
      await controller.enable(disclosureAccepted: true);
      expect(controller.state.status.active, true);
      await controller.sync(historyDays: 30);
      expect(platform.calls, containsAllInOrder(['history:30', 'sync']));
      expect(refreshes, 1);
      platform.allowed = false;
      await controller.refresh();
      expect(controller.state.status.active, false);
      final count = platform.calls.length;
      await controller.sync();
      expect(platform.calls.length, count);
    },
  );
  test(
    'permission alone never enables reading; off purges locally despite offline API',
    () async {
      platform.allowed = true;
      await controller.refresh();
      expect(controller.state.status.active, false);
      platform.grant = true;
      await controller.enable(disclosureAccepted: true);
      repo.failConsent = true;
      await controller.turnOff();
      expect(platform.enabled, false);
      expect(controller.state.status.active, false);
      expect(controller.state.message, contains('Stopped on this device'));
    },
  );
  test(
    'account switch while consent pending cannot enable or request permission',
    () async {
      repo.pending = Completer<SmsConsent>();
      final request = controller.enable(disclosureAccepted: true);
      await settle();
      identity = 'beta';
      repo.pending!.complete(
        const SmsConsent(
          accountId: 'alpha',
          available: true,
          enabled: true,
          version: '2026-10-22',
        ),
      );
      await request;
      expect(platform.calls, isEmpty);
    },
  );
  test(
    'off cancels stale sync publication and never replaces the disabled state',
    () async {
      platform.grant = true;
      await controller.enable(disclosureAccepted: true);
      platform.pendingSync = Completer<SmsImportStatus>();
      final sync = controller.sync();
      await settle();
      await controller.turnOff();
      platform.pendingSync!.complete(
        const SmsImportStatus(
          available: true,
          active: true,
          enabled: true,
          permission: true,
        ),
      );
      await sync;
      expect(controller.state.status.enabled, false);
      expect(refreshes, 0);
    },
  );
  test(
    'logout awaits native purge, and a failed purge preserves authentication',
    () async {
      final auth = AuthController(
        repo,
        FakeGoogleIdentity(),
        beforeSessionChange: platform.disable,
      );
      await settle();
      platform.failDisable = true;
      await expectLater(auth.logout(), throwsStateError);
      expect(auth.state.user?.id, 'alpha');
      expect(auth.state.loading, false);
      auth.dispose();
    },
  );
  test(
    'late import completion after screen disposal has no state effect',
    () async {
      platform.grant = true;
      await controller.enable(disclosureAccepted: true);
      platform.pendingSync = Completer<SmsImportStatus>();
      final request = controller.sync();
      await settle();
      controller.dispose();
      platform.pendingSync!.complete(const SmsImportStatus());
      await request;
      expect(refreshes, 0);
    },
  );

  testWidgets('unavailable local state can be cleared without enabling SMS', (
    tester,
  ) async {
    platform.localError = 'Local import state is unavailable.';
    await controller.refresh();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [mpesaControllerProvider.overrideWith((ref) => controller)],
        child: MaterialApp(
          theme: AppTheme.light(),
          home: const MpesaSettingsScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<FilledButton>(find.byKey(const Key('sms-enable')))
          .onPressed,
      isNull,
    );
    await tester.ensureVisible(find.text('Clear local import data'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Clear local import data'));
    await tester.pumpAndSettle();
    expect(platform.calls, ['disable']);
    expect(controller.state.status.error, isNull);
    expect(controller.state.status.enabled, isFalse);
  });

  testWidgets('enable always opens disclosure before any permission request', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [mpesaControllerProvider.overrideWith((ref) => controller)],
        child: MaterialApp(
          theme: AppTheme.light(),
          home: const MpesaSettingsScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sms-enable')));
    await tester.pumpAndSettle();
    expect(find.text('Allow optional M-PESA import?'), findsOneWidget);
    expect(platform.calls, isEmpty);
    expect(repo.calls, isEmpty);
    await tester.tap(find.text('Keep off'));
    await tester.pumpAndSettle();
    expect(controller.state.status.enabled, false);
    expect(platform.calls, isEmpty);
  });
  testWidgets('settings and disclosure fit narrow 200 percent text', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [mpesaControllerProvider.overrideWith((ref) => controller)],
        child: MaterialApp(
          theme: AppTheme.light(),
          builder: (context, child) => MediaQuery(
            data: MediaQuery.of(
              context,
            ).copyWith(textScaler: const TextScaler.linear(2)),
            child: child!,
          ),
          home: const MpesaSettingsScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(find.byKey(const Key('sms-enable')), 200);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sms-enable')));
    await tester.pumpAndSettle();
    expect(find.text(smsDisclosure), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
