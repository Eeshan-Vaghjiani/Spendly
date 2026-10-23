// Disposable emulator only. Install over the completed acceptance package to
// exercise real app startup without the integration-test runner or fixture reset.
import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:package_info_plus/package_info_plus.dart';
import 'package:spending_support/main.dart' as spendly;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  const base = String.fromEnvironment('API_BASE_URL');
  final uri = Uri.parse(base);
  final package = await PackageInfo.fromPlatform();
  final status = await const MethodChannel(
    'spendly/mpesa_sms',
  ).invokeMapMethod<String, dynamic>('status');
  if (!const bool.fromEnvironment('SPENDLY_ACCEPTANCE_BUILD') ||
      !const bool.fromEnvironment('SPENDLY_SMS_EMULATOR_LAB') ||
      status?['emulator_lab'] != true ||
      package.packageName != 'com.evagh.capstone.spending_support.acceptance' ||
      uri.scheme != 'http' ||
      uri.host != '127.0.0.1' ||
      uri.port != 5057 ||
      uri.path != '/api/v1') {
    throw StateError('Only the disposable SMS emulator lab is allowed.');
  }
  final transport = http.Client();
  try {
    final target = jsonDecode(
      (await transport
              .get(Uri.parse('$base/sms-acceptance-target'))
              .timeout(const Duration(seconds: 10)))
          .body,
    )['data'];
    final phase = jsonDecode(
      (await transport
              .get(Uri.parse('$base/sms-lab-checkpoint'))
              .timeout(const Duration(seconds: 10)))
          .body,
    )['data']['phase'];
    if (target['disposable'] != true ||
        target['database'] != 'in_memory' ||
        phase != 'complete') {
      throw StateError('Complete the disposable acceptance suite first.');
    }
  } finally {
    transport.close();
  }
  spendly.main();
}
