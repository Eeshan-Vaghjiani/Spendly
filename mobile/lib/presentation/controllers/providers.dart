import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/config/app_config.dart';
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
  return ApiSpendingRepository(
    ApiClient(
      baseUrl: AppConfig.apiBaseUrl,
      tokenStore: ref.watch(tokenStoreProvider),
    ),
  );
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
  AuthController(this._repository, this._googleIdentity)
    : super(const AuthState(loading: true)) {
    restore();
  }

  final SpendingRepository _repository;
  final GoogleIdentityProvider _googleIdentity;

  bool get googleSignInConfigured => _googleIdentity.isConfigured;

  Future<void> restore() async {
    final user = await _repository.restoreSession();
    state = AuthState(user: user, initialized: true);
  }

  Future<bool> login(String email, String password) async {
    state = state.copyWith(loading: true, clearError: true);
    try {
      final user = await _repository.login(email, password);
      state = AuthState(user: user, initialized: true);
      return true;
    } catch (error) {
      state = AuthState(error: error.toString(), initialized: true);
      return false;
    }
  }

  Future<bool> loginWithGoogle() async {
    state = state.copyWith(loading: true, clearError: true);
    try {
      final idToken = await _googleIdentity.authenticate();
      final user = await _repository.loginWithGoogle(idToken);
      state = AuthState(user: user, initialized: true);
      return true;
    } catch (error) {
      state = AuthState(error: error.toString(), initialized: true);
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
      state = AuthState(user: user, initialized: true);
      return true;
    } catch (error) {
      state = AuthState(error: error.toString(), initialized: true);
      return false;
    }
  }

  Future<bool> updateConsent({required bool modelTrainingOptIn}) async {
    state = state.copyWith(loading: true, clearError: true);
    try {
      final user = await _repository.updateConsent(
        acceptedTerms: true,
        acceptedPrivacy: true,
        modelTrainingOptIn: modelTrainingOptIn,
      );
      state = AuthState(user: user, initialized: true);
      return true;
    } catch (error) {
      state = AuthState(
        user: state.user,
        error: error.toString(),
        initialized: true,
      );
      return false;
    }
  }

  Future<void> logout() async {
    try {
      await _googleIdentity.signOut();
    } finally {
      await _repository.logout();
    }
    state = const AuthState(initialized: true);
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

class AnalysisState {
  const AnalysisState({this.result, this.loading = false, this.error});

  final AnalysisResult? result;
  final bool loading;
  final String? error;
}

class AnalysisController extends StateNotifier<AnalysisState> {
  AnalysisController(this._repository) : super(const AnalysisState());

  final SpendingRepository _repository;

  Future<void> loadLatest() async {
    state = AnalysisState(result: state.result, loading: true);
    try {
      state = AnalysisState(result: await _repository.latestAnalysis());
    } catch (error) {
      state = AnalysisState(result: state.result, error: error.toString());
    }
  }

  Future<void> run() async {
    state = AnalysisState(result: state.result, loading: true);
    try {
      state = AnalysisState(result: await _repository.runAnalysis());
    } catch (error) {
      state = AnalysisState(result: state.result, error: error.toString());
    }
  }
}

final analysisControllerProvider =
    StateNotifierProvider<AnalysisController, AnalysisState>((ref) {
      return AnalysisController(ref.watch(repositoryProvider));
    });
