import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/config/app_config.dart';
import '../../core/network/api_exception.dart';
import '../../data/models/models.dart';
import '../../data/repositories/api_spending_repository.dart';
import '../../data/services/api_client.dart';
import '../../data/services/google_identity_service.dart';
import '../../data/services/token_store.dart';
import '../../domain/repositories/spending_repository.dart';

final tokenStoreProvider = Provider<TokenStore>((ref) => SecureTokenStore());

final googleIdentityProvider = Provider<GoogleIdentityProvider>(
  (ref) => GoogleIdentityService(),
);

final repositoryProvider = Provider<SpendingRepository>((ref) {
  final api = ApiClient(
    baseUrl: AppConfig.apiBaseUrl,
    tokenStore: ref.watch(tokenStoreProvider),
  );
  ref.onDispose(api.close);
  return ApiSpendingRepository(api);
});

class AuthState {
  const AuthState({
    this.user,
    this.loading = false,
    this.error,
    this.initialized = false,
  });

  final UserProfile? user;
  final bool loading;
  final String? error;
  final bool initialized;

  AuthState copyWith({
    UserProfile? user,
    bool? loading,
    String? error,
    bool clearError = false,
    bool clearUser = false,
    bool? initialized,
  }) => AuthState(
    user: clearUser ? null : user ?? this.user,
    loading: loading ?? this.loading,
    error: clearError ? null : error ?? this.error,
    initialized: initialized ?? this.initialized,
  );
}

class AuthController extends StateNotifier<AuthState> {
  AuthController(
    this._repository,
    this._googleIdentity, {
    this.googleCleanupTimeout = const Duration(seconds: 5),
  }) : super(const AuthState(loading: true)) {
    restore();
  }

  final SpendingRepository _repository;

  final GoogleIdentityProvider _googleIdentity;
  final Duration googleCleanupTimeout;
  int _generation = 0;
  Future<void>? _logoutTask;
  Future<void>? _googleCleanup;

  bool _current(int generation) => mounted && generation == _generation;

  String _accountError(Object error) =>
      error is ApiException || error is GoogleIdentityException
      ? error.toString()
      : 'Could not complete this account request. Please try again.';

  bool get googleSignInConfigured => _googleIdentity.isConfigured;

  Future<void> restore() async {
    if (!mounted || _logoutTask != null) return;
    final generation = ++_generation;
    state = const AuthState(loading: true);
    try {
      final user = await _repository.restoreSession();
      if (_current(generation)) {
        state = AuthState(user: user, initialized: true);
      }
    } catch (_) {
      if (_current(generation)) {
        state = const AuthState(
          error: 'Could not open your saved session. Please try again.',
        );
      }
    }
  }

  Future<bool> login(String email, String password) async {
    if (!mounted || state.loading) return false;
    final generation = ++_generation;
    state = state.copyWith(loading: true, clearError: true);
    try {
      final user = await _repository.login(email, password);
      if (!_current(generation)) return false;
      state = AuthState(user: user, initialized: true);
      return true;
    } catch (error) {
      if (!_current(generation)) return false;
      state = AuthState(error: _accountError(error), initialized: true);
      return false;
    }
  }

  Future<bool> loginWithGoogle() async {
    if (!mounted || state.loading) return false;
    if (_googleCleanup != null) {
      state = state.copyWith(
        error:
            'Google sign-out is still finishing. Try again or sign in with email.',
      );
      return false;
    }
    final generation = ++_generation;
    state = state.copyWith(loading: true, clearError: true);
    try {
      final idToken = await _googleIdentity.authenticate();
      if (!_current(generation)) return false;
      final user = await _repository.loginWithGoogle(idToken);
      if (!_current(generation)) return false;
      state = AuthState(user: user, initialized: true);
      return true;
    } catch (error) {
      if (!_current(generation)) return false;
      state = AuthState(error: _accountError(error), initialized: true);
      return false;
    }
  }

  Future<bool> register(
    String email,
    String password,
    String displayName, {
    required bool acceptedTerms,
    required bool acceptedPrivacy,
    required bool modelTrainingOptIn,
  }) async {
    if (!mounted || state.loading) return false;
    final generation = ++_generation;
    state = state.copyWith(loading: true, clearError: true);
    try {
      final user = await _repository.register(
        email,
        password,
        displayName,
        acceptedTerms: acceptedTerms,
        acceptedPrivacy: acceptedPrivacy,
        modelTrainingOptIn: modelTrainingOptIn,
      );
      if (!_current(generation)) return false;
      state = AuthState(user: user, initialized: true);
      return true;
    } catch (error) {
      if (!_current(generation)) return false;
      state = AuthState(error: _accountError(error), initialized: true);
      return false;
    }
  }

  Future<bool> updateConsent({required bool modelTrainingOptIn}) async {
    if (!mounted || state.loading) return false;
    final generation = ++_generation;
    state = state.copyWith(loading: true, clearError: true);
    try {
      final user = await _repository.updateConsent(
        acceptedTerms: true,
        acceptedPrivacy: true,
        modelTrainingOptIn: modelTrainingOptIn,
      );
      if (!_current(generation)) return false;
      state = AuthState(user: user, initialized: true);
      return true;
    } catch (error) {
      if (!_current(generation)) return false;
      state = AuthState(
        user: state.user,
        error: _accountError(error),
        initialized: true,
      );
      return false;
    }
  }

  Future<bool> updateUsername(String username) async {
    if (!mounted || state.loading) return false;
    final generation = ++_generation;
    state = state.copyWith(loading: true, clearError: true);
    try {
      final user = await _repository.updateUsername(username);
      if (!_current(generation)) return false;
      state = AuthState(user: user, initialized: true);
      return true;
    } catch (error) {
      if (!_current(generation)) return false;
      state = AuthState(
        user: state.user,
        error: _accountError(error),
        initialized: true,
      );
      return false;
    }
  }

  Future<bool> completeOnboarding({required bool skipped}) async {
    if (!mounted || state.loading) return false;
    final generation = ++_generation;
    state = state.copyWith(loading: true, clearError: true);
    try {
      final user = await _repository.completeOnboarding(skipped: skipped);
      if (!_current(generation)) return false;
      state = AuthState(user: user, initialized: true);
      return true;
    } catch (error) {
      if (!_current(generation)) return false;
      state = AuthState(
        user: state.user,
        error: _accountError(error),
        initialized: true,
      );
      return false;
    }
  }

  Future<void> logout() {
    if (!mounted) return Future.value();
    return _logoutTask ??= _performLogout().whenComplete(
      () => _logoutTask = null,
    );
  }

  Future<void> _performLogout() async {
    final generation = ++_generation;
    final previous = state;
    state = state.copyWith(loading: true, clearError: true);
    try {
      await _repository.logout();
    } catch (_) {
      if (_current(generation)) state = previous.copyWith(loading: false);
      rethrow;
    }
    if (!_current(generation)) return;
    state = const AuthState(initialized: true, loading: true);
    final cleanup = Future<void>.sync(
      _googleIdentity.signOut,
    ).catchError((Object _) {});
    _googleCleanup = cleanup;
    unawaited(
      cleanup.then((_) {
        if (identical(_googleCleanup, cleanup)) _googleCleanup = null;
      }),
    );
    try {
      await cleanup.timeout(googleCleanupTimeout);
    } catch (_) {
      // A hung provider must not block local logout or email sign-in. Google
      // sign-in stays gated until the original cleanup actually settles.
    }
    if (_current(generation)) state = const AuthState(initialized: true);
  }

  @override
  void dispose() {
    ++_generation;
    super.dispose();
  }
}

final authControllerProvider = StateNotifierProvider<AuthController, AuthState>(
  (ref) {
    return AuthController(
      ref.watch(repositoryProvider),
      ref.watch(googleIdentityProvider),
    );
  },
);

final dashboardPeriodProvider = StateProvider<String>((ref) => 'monthly');

class AnalysisState {
  const AnalysisState({this.result, this.loading = false, this.error});

  final AnalysisResult? result;
  final bool loading;
  final String? error;
}

class AnalysisController extends StateNotifier<AnalysisState> {
  AnalysisController(this._repository) : super(const AnalysisState());

  final SpendingRepository _repository;
  int _generation = 0;
  DateTime? historyCompleteFrom;

  Future<void> loadLatest() async {
    final generation = ++_generation;
    state = AnalysisState(result: state.result, loading: true);
    try {
      final result = await _repository.latestAnalysis();
      if (mounted && generation == _generation) {
        state = AnalysisState(result: result);
      }
    } catch (error) {
      if (mounted && generation == _generation) {
        state = AnalysisState(result: state.result, error: error.toString());
      }
    }
  }

  Future<void> run() async {
    final generation = ++_generation;
    state = AnalysisState(result: state.result, loading: true);
    try {
      final result = await _repository.runAnalysis(
        historyCompleteFrom: historyCompleteFrom,
      );
      if (mounted && generation == _generation) {
        state = AnalysisState(result: result);
      }
    } catch (error) {
      if (mounted && generation == _generation) {
        state = AnalysisState(result: state.result, error: error.toString());
      }
    }
  }
}

final analysisControllerProvider =
    StateNotifierProvider<AnalysisController, AnalysisState>((ref) {
      ref.watch(authControllerProvider.select((state) => state.user?.id));
      return AnalysisController(ref.watch(repositoryProvider));
    });
