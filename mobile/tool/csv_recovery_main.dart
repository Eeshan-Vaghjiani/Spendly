// Debug-only synthetic entrypoint: restore real secure storage, then run the
// normal app. No integration-test runner survives/restarts the app for us.
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:spending_support/data/repositories/api_spending_repository.dart';
import 'package:spending_support/data/services/api_client.dart';
import 'package:spending_support/data/services/token_store.dart';
import 'package:spending_support/main.dart' as spendly;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  const base = String.fromEnvironment('API_BASE_URL');
  final package = await PackageInfo.fromPlatform();
  if (!kDebugMode ||
      !const bool.fromEnvironment('SPENDLY_ACCEPTANCE_BUILD') ||
      const bool.fromEnvironment('SPENDLY_SMS_CAPABILITY') ||
      package.packageName != 'com.evagh.capstone.spending_support.acceptance' ||
      base != 'http://127.0.0.1:5057/api/v1') {
    throw StateError(
      'Only the separate disposable CSV acceptance build is allowed.',
    );
  }
  final api = ApiClient(baseUrl: base, tokenStore: SecureTokenStore());
  try {
    final target = await api.request(
      'GET',
      '/csv-recovery-target',
      authenticated: false,
    );
    if (target['disposable'] != true ||
        target['database'] != 'in_memory' ||
        target['scenario'] != 'csv_recovery') {
      throw StateError('The disposable CSV fixture is required.');
    }
    final repository = ApiSpendingRepository(api);
    var user = await repository.restoreSession();
    final restored = user != null;
    if (!restored) {
      if (target['bootstrap_allowed'] != true) {
        throw StateError('Session was lost after the first launch.');
      }
      user = await repository.login(
        'csv-recovery@example.invalid',
        'SyntheticNativeOnly123!',
      );
    }
    if (user.id != target['account_id']) {
      throw StateError('Unexpected synthetic account.');
    }
    await api.request(
      'POST',
      '/csv-recovery-ready',
      body: {'restored': restored},
    );
  } finally {
    api.close();
  }
  spendly.main();
}
