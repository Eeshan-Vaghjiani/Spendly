import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/foundation.dart';

import '../../core/config/app_config.dart';
import '../../data/models/mpesa_models.dart';
import '../../data/services/mpesa_platform.dart';
import '../../domain/repositories/spending_repository.dart';
import 'providers.dart';

class MpesaScreenState {
  const MpesaScreenState({
    this.status = const SmsImportStatus(),
    this.consent,
    this.busy = false,
    this.message,
  });
  final SmsImportStatus status;
  final SmsConsent? consent;
  final bool busy;
  final String? message;
}

class MpesaController extends StateNotifier<MpesaScreenState> {
  MpesaController(
    this.repository,
    this.platform,
    this.owner,
    this.currentOwner,
    this.sessionReady,
    this.token,
    this.changed, {
    this.baseUrl = AppConfig.apiBaseUrl,
  }) : super(const MpesaScreenState(busy: true)) {
    refresh();
  }
  final SpendingRepository repository;
  final MpesaPlatform platform;
  final String? owner;
  final String? Function() currentOwner;
  final bool Function() sessionReady;
  final Future<String?> Function() token;
  final void Function() changed;
  final String baseUrl;
  int _generation = 0;
  bool _stopping = false;
  bool _current(int generation) =>
      mounted &&
      generation == _generation &&
      owner != null &&
      currentOwner() == owner &&
      sessionReady();
  void _finish(int generation) {
    if (mounted && generation == _generation) {
      state = MpesaScreenState(
        status: state.status,
        consent: state.consent,
        message: state.message,
      );
    }
  }

  void _message(String value) => state = MpesaScreenState(
    status: state.status,
    consent: state.consent,
    busy: true,
    message: value,
  );

  Future<void> refresh() async {
    final generation = ++_generation;
    state = MpesaScreenState(
      status: state.status,
      consent: state.consent,
      busy: true,
    );
    try {
      var status = await platform.status(); // Own settings only, never SMS.
      if (!_current(generation)) return;
      state = MpesaScreenState(
        status: status,
        consent: state.consent,
        busy: true,
      );
      if (!status.available) {
        state = MpesaScreenState(status: status);
        return;
      }
      final consent = await repository.smsConsent();
      if (!_current(generation)) return;
      if (consent.accountId != owner) {
        throw StateError('Session identity mismatch');
      }
      if (status.enabled &&
          (!consent.enabled ||
              !consent.available ||
              consent.version != consent.requiredVersion)) {
        await platform.disable();
        status = await platform.status();
      }
      if (_current(generation)) {
        state = MpesaScreenState(status: status, consent: consent);
      }
    } catch (error) {
      if (kDebugMode) {
        debugPrint('SMS settings check failed: ${error.runtimeType}');
      }
      if (_current(generation)) {
        _message(
          'Could not check service settings. Check the device status and your connection before enabling or syncing.',
        );
      }
    } finally {
      _finish(generation);
    }
  }

  Future<void> enable({required bool disclosureAccepted}) async {
    if (!disclosureAccepted ||
        state.busy ||
        !state.status.available ||
        state.consent?.available != true) {
      return;
    }
    final generation = ++_generation;
    state = MpesaScreenState(
      status: state.status,
      consent: state.consent,
      busy: true,
    );
    try {
      if (!_current(generation)) return;
      final consent = await repository.updateSmsConsent(
        enabled: true,
        disclosureAccepted: true,
        version: state.consent!.requiredVersion,
      );
      if (!_current(generation)) return;
      if (!consent.enabled ||
          consent.accountId != owner ||
          consent.version != consent.requiredVersion) {
        throw StateError('Consent not confirmed');
      }
      final credential = await token();
      if (!_current(generation)) return;
      if (credential == null) throw StateError('Session unavailable');
      await platform.enable(
        accountId: owner!,
        token: credential,
        baseUrl: baseUrl,
        version: consent.requiredVersion,
      );
      if (!_current(generation)) return;
      await platform.requestPermission(consent.requiredVersion);
      if (!_current(generation)) return;
      final status = await platform.status();
      if (_current(generation)) {
        state = MpesaScreenState(
          status: status,
          consent: consent,
          message: status.permission
              ? null
              : 'Permission required. SMS import is inactive.',
        );
      }
    } catch (error) {
      if (kDebugMode) debugPrint('SMS enable failed: ${error.runtimeType}');
      if (_current(generation)) {
        try {
          await platform.disable();
        } catch (_) {
          /* Native failure stays visible. */
        }
        if (_current(generation)) {
          _message(
            'SMS import could not be enabled safely. Check your connection and try again.',
          );
        }
      }
    } finally {
      _finish(generation);
    }
  }

  Future<void> turnOff() async {
    if (_stopping) return;
    _stopping = true;
    final generation =
        ++_generation; // Cancels any late enable/sync completion.
    state = MpesaScreenState(
      status: state.status,
      consent: state.consent,
      busy: true,
    );
    try {
      await platform.disable(); // Purge first, independently of network access.
      if (!_current(generation)) return;
      final status = await platform.status();
      if (!_current(generation)) return;
      state = MpesaScreenState(
        status: status,
        consent: state.consent,
        busy: true,
      );
      try {
        final consent = await repository.updateSmsConsent(enabled: false);
        if (_current(generation)) {
          state = MpesaScreenState(status: status, consent: consent);
        }
      } catch (_) {
        if (_current(generation)) {
          _message(
            'Stopped on this device. The service setting could not be updated; reconnect and turn it off again.',
          );
        }
      }
    } catch (_) {
      if (_current(generation)) {
        _message(
          'Could not save the disabled setting. Keep this screen open and retry before signing out.',
        );
      }
    } finally {
      _stopping = false;
      _finish(generation);
    }
  }

  Future<void> sync({int? historyDays}) async {
    if (state.busy || !state.status.active) return;
    final generation = ++_generation;
    state = MpesaScreenState(
      status: state.status,
      consent: state.consent,
      busy: true,
    );
    try {
      if (!_current(generation)) return;
      if (historyDays != null) await platform.historical(historyDays);
      if (!_current(generation)) return;
      final status = await platform.sync();
      if (!_current(generation)) return;
      state = MpesaScreenState(
        status: status,
        consent: state.consent,
        message: status.error,
      );
      if ((status.summary['created'] ?? 0) > 0 ||
          (status.summary['reversals'] ?? 0) > 0) {
        changed();
      }
    } catch (_) {
      if (_current(generation)) {
        _message(
          'Sync could not finish. Pending normalized records are kept for an idempotent retry.',
        );
      }
    } finally {
      _finish(generation);
    }
  }

  @override
  void dispose() {
    ++_generation;
    super.dispose();
  }
}

final mpesaControllerProvider =
    StateNotifierProvider.autoDispose<MpesaController, MpesaScreenState>((ref) {
      final owner = ref.watch(
        authControllerProvider.select((value) => value.user?.id),
      );
      return MpesaController(
        ref.watch(repositoryProvider),
        ref.watch(mpesaPlatformProvider),
        owner,
        () => ref.read(authControllerProvider).user?.id,
        () => !ref.read(authControllerProvider).loading,
        () => ref.read(apiClientProvider).readToken(),
        () => ref.read(financialDataRevisionProvider.notifier).state++,
      );
    });
