import 'package:flutter/services.dart';

import '../models/mpesa_models.dart';

abstract class MpesaPlatform {
  Stream<void> get changes;
  Future<SmsImportStatus> status();
  Future<void> disable();
  Future<void> refreshSession(String accountId, String token);
  Future<void> enable({
    required String accountId,
    required String token,
    required String baseUrl,
    required String version,
  });
  Future<bool> requestPermission(String acceptedVersion);
  Future<void> historical(int days);
  Future<SmsImportStatus> sync();
}

class NoSmsPlatform implements MpesaPlatform {
  @override
  Stream<void> get changes => const Stream.empty();
  @override
  Future<SmsImportStatus> status() async => const SmsImportStatus();
  @override
  Future<void> disable() async {}
  @override
  Future<void> refreshSession(String accountId, String token) async {}
  @override
  Future<void> enable({
    required String accountId,
    required String token,
    required String baseUrl,
    required String version,
  }) async => throw StateError('SMS capability unavailable');
  @override
  Future<bool> requestPermission(String acceptedVersion) async => false;
  @override
  Future<void> historical(int days) async {}
  @override
  Future<SmsImportStatus> sync() => status();
}

class AndroidMpesaPlatform implements MpesaPlatform {
  AndroidMpesaPlatform({MethodChannel? channel})
    : _channel = channel ?? const MethodChannel('spendly/mpesa_sms');
  final MethodChannel _channel;
  static const _events = EventChannel('spendly/mpesa_changes');
  @override
  Stream<void> get changes => _events.receiveBroadcastStream().map((_) {});
  Future<SmsImportStatus> _status(String method) async =>
      SmsImportStatus.fromJson(
        Map<String, dynamic>.from(
          await _channel.invokeMapMethod<String, dynamic>(method) ?? {},
        ),
      );
  @override
  Future<SmsImportStatus> status() => _status('status');
  @override
  Future<void> disable() async {
    await _channel.invokeMethod<void>('disable');
  }

  @override
  Future<void> refreshSession(String accountId, String token) async {
    await _channel.invokeMethod<void>('refreshSession', {
      'account_id': accountId,
      'token': token,
    });
  }

  @override
  Future<void> enable({
    required String accountId,
    required String token,
    required String baseUrl,
    required String version,
  }) async {
    await _channel.invokeMethod<void>('enable', {
      'account_id': accountId,
      'token': token,
      'base_url': baseUrl,
      'consent_version': version,
    });
  }

  @override
  Future<bool> requestPermission(String acceptedVersion) async =>
      await _channel.invokeMethod<bool>('requestPermission', {
        'accepted': true,
        'consent_version': acceptedVersion,
      }) ??
      false;
  @override
  Future<void> historical(int days) async {
    await _channel.invokeMethod<void>('historical', {'days': days});
  }

  @override
  Future<SmsImportStatus> sync() => _status('sync');
}
