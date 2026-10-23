import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:spending_support/core/theme/app_theme.dart';
import 'package:spending_support/data/repositories/api_spending_repository.dart';
import 'package:spending_support/data/services/api_client.dart';
import 'package:spending_support/data/services/mpesa_platform.dart';
import 'package:spending_support/data/services/token_store.dart';
import 'package:spending_support/presentation/controllers/mpesa_controller.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/mpesa_settings_screen.dart';

class _ObservedNative extends AndroidMpesaPlatform {
  @override
  Future<void> enable({
    required String accountId,
    required String token,
    required String baseUrl,
    required String version,
  }) async {
    debugPrint('SMS_NATIVE:enable');
    try {
      await super.enable(
        accountId: accountId,
        token: token,
        baseUrl: baseUrl,
        version: version,
      );
    } on PlatformException catch (error) {
      debugPrint(
        'SMS_NATIVE:enable:${error.code}:${error.details is Map ? error.details['reason'] : 'no-class'}',
      );
      rethrow;
    }
  }

  @override
  Future<bool> requestPermission(String acceptedVersion) async {
    debugPrint('SMS_NATIVE:contextual-permission');
    return super.requestPermission(acceptedVersion);
  }
}

Future<void> main() async {
  const base = String.fromEnvironment('ACCEPTANCE_API_BASE_URL');
  const lifecycleHarness = bool.fromEnvironment(
    'SPENDLY_SMS_LIFECYCLE_HARNESS',
  );
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  const channel = MethodChannel('spendly/mpesa_sms');
  testWidgets(
    'consent, actual emulator inbox, receiver, offline retry and off',
    (tester) async {
      final uri = Uri.parse(base);
      final package = await PackageInfo.fromPlatform();
      if (uri.scheme != 'http' ||
          uri.host != '127.0.0.1' ||
          uri.port != 5057 ||
          uri.path != '/api/v1' ||
          package.packageName !=
              'com.evagh.capstone.spending_support.acceptance') {
        throw StateError(
          'Only the disposable emulator and loopback lab are allowed.',
        );
      }
      final native = _ObservedNative();
      final initial = await channel.invokeMapMethod<String, dynamic>('status');
      if (initial?['emulator_lab'] != true) {
        throw StateError('Real inbox tests require a disposable emulator.');
      }
      final storage = SecureTokenStore();
      final api = ApiClient(baseUrl: base, tokenStore: storage);
      addTearDown(api.close);
      final target = await api.request(
        'GET',
        '/sms-acceptance-target',
        authenticated: false,
      );
      if (target['database'] != 'in_memory' ||
          target['disposable'] != true ||
          target['mpesa_sms'] != true) {
        throw StateError('Disposable SMS service attestation failed.');
      }
      // Keep synthetic test coordination reachable when the app's ADB reverse
      // data transport is deliberately disconnected. Both paths must attest
      // to the same disposable process before touching test state.
      final control = ApiClient(
        baseUrl: 'http://10.0.2.2:5057/api/v1',
        tokenStore: storage,
      );
      addTearDown(control.close);
      final controlTarget = await control.request(
        'GET',
        '/sms-acceptance-target',
        authenticated: false,
      );
      if (target['lab_id'] == null ||
          target['lab_id'] != controlTarget['lab_id']) {
        throw StateError('Control and data must use the same disposable lab.');
      }
      await native.disable();
      await storage.clear();
      final repository = ApiSpendingRepository(api);
      await repository.register(
        'sms-native-alpha@example.invalid',
        'SyntheticNativeOnly123!',
        'SMS Alpha',
        acceptedTerms: true,
        acceptedPrivacy: true,
        modelTrainingOptIn: false,
      );
      await repository.completeOnboarding(skipped: true);

      Future<void> checkpoint(String phase) async {
        debugPrint('SPENDLY_SMS:$phase');
        final acknowledged = await tester.runAsync(() async {
          await control.request(
            'POST',
            '/sms-lab-checkpoint',
            authenticated: false,
            body: {'phase': phase},
          );
          for (var i = 0; i < 120; i++) {
            final data = await control.request(
              'GET',
              '/sms-lab-checkpoint',
              authenticated: false,
              retryOnce: false,
            );
            if (data['ack'] == true) return true;
            await Future<void>.delayed(const Duration(seconds: 1));
          }
          return false;
        });
        expect(
          acknowledged,
          isTrue,
          reason: 'Host did not complete synthetic phase $phase',
        );
      }

      Future<void> rows(int expected) async {
        final ready = await tester.runAsync(() async {
          for (var i = 0; i < 90; i++) {
            if ((await repository.transactions()).length == expected) {
              return true;
            }
            await Future<void>.delayed(const Duration(seconds: 1));
          }
          return false;
        });
        expect(
          ready,
          isTrue,
          reason: 'Expected $expected normalized transaction rows',
        );
      }

      Future<void> pending() async {
        final queued = await tester.runAsync(() async {
          for (var i = 0; i < 80; i++) {
            if ((await native.status()).pending > 0) return true;
            await Future<void>.delayed(const Duration(milliseconds: 500));
          }
          return false;
        });
        expect(queued, isTrue, reason: 'Synthetic SMS was not queued offline');
      }

      await checkpoint('seed_history');
      expect((await native.status()).enabled, isFalse);
      expect(
        (await channel.invokeMapMethod<String, dynamic>(
          'status',
        ))!['test_sms_reads'],
        0,
      );
      expect(await repository.transactions(), isEmpty);

      final container = ProviderContainer(
        overrides: [
          repositoryProvider.overrideWithValue(repository),
          apiClientProvider.overrideWithValue(api),
          tokenStoreProvider.overrideWithValue(storage),
          mpesaPlatformProvider.overrideWithValue(native),
        ],
      );
      addTearDown(container.dispose);
      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            theme: AppTheme.light(),
            home: const MpesaSettingsScreen(),
          ),
        ),
      );
      for (var i = 0; i < 100; i++) {
        await tester.pump(const Duration(milliseconds: 100));
        if (!container.read(authControllerProvider).loading &&
            !container.read(mpesaControllerProvider).busy) {
          break;
        }
      }
      expect(find.text('Off'), findsOneWidget);
      await tester.tap(find.byKey(const Key('sms-enable')));
      await tester.pumpAndSettle();
      expect(find.text('Allow optional M-PESA import?'), findsOneWidget);
      expect(
        (await channel.invokeMapMethod<String, dynamic>(
          'status',
        ))!['test_sms_reads'],
        0,
      );
      // The host approves only this contextual OS dialog on the empty emulator.
      await control.request(
        'POST',
        '/sms-lab-checkpoint',
        authenticated: false,
        body: {'phase': 'permission'},
      );
      await tester.tap(find.byKey(const Key('sms-accept-disclosure')));
      for (var i = 0; i < 300; i++) {
        await tester.pump(const Duration(milliseconds: 200));
        if (find.text('Last 30 days').evaluate().isNotEmpty) break;
      }
      expect(find.text('Last 30 days'), findsOneWidget);
      await tester.pumpAndSettle();
      await tester.ensureVisible(find.text('Last 30 days'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Last 30 days'));
      await tester.pump(const Duration(seconds: 1));
      await rows(4);
      final transactions = await repository.transactions();
      expect(transactions.every((row) => row.source == 'mpesa_sms'), isTrue);
      expect(
        transactions
            .where((row) => row.transactionType == 'income')
            .single
            .amount,
        2345.60,
      );
      expect(
        transactions
            .where((row) => row.category == 'transaction_fees')
            .single
            .amount,
        8.50,
      );
      expect(
        transactions
            .where((row) => row.category == 'airtime_and_data')
            .single
            .amount,
        75.00,
      );

      await checkpoint('background');
      await rows(5);
      await checkpoint('offline');
      await pending();
      await checkpoint('reconnect');
      await rows(6);
      await checkpoint('duplicate');
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(seconds: 4)),
      );
      expect((await repository.transactions()).length, 6);
      await checkpoint('foreground');
      await tester.pump(const Duration(seconds: 1));
      await container.read(mpesaControllerProvider.notifier).turnOff();
      final stoppedReads = (await channel.invokeMapMethod<String, dynamic>(
        'status',
      ))!['test_sms_reads'];
      await checkpoint('off_delivery');
      expect((await native.status()).active, isFalse);
      expect((await native.status()).pending, 0);
      expect(
        (await channel.invokeMapMethod<String, dynamic>(
          'status',
        ))!['test_sms_reads'],
        stoppedReads,
      );
      expect((await repository.transactions()).length, 6);
      expect((await repository.smsConsent()).enabled, isFalse);
      // Re-consent to the same disclosure, then leave a real encrypted queue
      // offline while the real auth controller signs out and changes account.
      await container
          .read(mpesaControllerProvider.notifier)
          .enable(disclosureAccepted: true);
      expect((await native.status()).active, isTrue);
      await checkpoint('pending_logout');
      await pending();
      await container.read(authControllerProvider.notifier).logout();
      expect((await native.status()).enabled, isFalse);
      expect((await native.status()).pending, 0);
      await checkpoint('after_logout');
      await repository.register(
        'sms-native-beta@example.invalid',
        'SyntheticNativeOnly123!',
        'SMS Beta',
        acceptedTerms: true,
        acceptedPrivacy: true,
        modelTrainingOptIn: false,
      );
      await container.read(authControllerProvider.notifier).restore();
      expect((await repository.smsConsent()).enabled, isFalse);
      expect((await native.status()).active, isFalse);
      expect((await native.status()).permission, isTrue);
      await checkpoint('beta_delivery');
      expect(await repository.transactions(), isEmpty);
      expect(
        await container
            .read(authControllerProvider.notifier)
            .login(
              'sms-native-alpha@example.invalid',
              'SyntheticNativeOnly123!',
            ),
        isTrue,
      );
      expect((await repository.transactions()).length, 6);
      expect((await native.status()).enabled, isFalse);
      expect(tester.takeException(), isNull);
      if (lifecycleHarness) {
        await container.read(mpesaControllerProvider.notifier).refresh();
        await container
            .read(mpesaControllerProvider.notifier)
            .enable(disclosureAccepted: true);
        expect((await native.status()).active, isTrue);
      }
      await checkpoint('complete');
    },
    timeout: const Timeout(Duration(minutes: 9)),
  );
}
