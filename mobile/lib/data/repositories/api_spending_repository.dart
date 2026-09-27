import '../../domain/repositories/spending_repository.dart';
import '../../core/network/api_exception.dart';
import '../models/models.dart';
import '../services/api_client.dart';

class ApiSpendingRepository implements SpendingRepository {
  ApiSpendingRepository(this._api);

  final ApiClient _api;

  @override
  Future<UserProfile?> restoreSession() async {
    if (await _api.readToken() == null) return null;
    try {
      final data = await _api.request('POST', '/auth/renew');
      await _api.saveToken(data['access_token'] as String);
      final user = data['user'] as Map<String, dynamic>;
      await _api.saveCachedUser(user);
      return UserProfile.fromJson(user);
    } on ApiException catch (error) {
      if (error.statusCode == 401) {
        await _api.clearToken();
        return null;
      }
      return _restoreCachedUser();
    } catch (_) {
      return _restoreCachedUser();
    }
  }

  Future<UserProfile?> _restoreCachedUser() async {
    final cached = await _api.readCachedUser();
    return cached == null ? null : UserProfile.fromJson(cached);
  }

  @override
  Future<UserProfile> login(String email, String password) =>
      _authenticate('/auth/login', {'email': email, 'password': password});

  @override
  Future<UserProfile> loginWithGoogle(String idToken) =>
      _authenticate('/auth/google', {'id_token': idToken});

  @override
  Future<UserProfile> register(
    String email,
    String password,
    String displayName, {
    required bool acceptedTerms,
    required bool acceptedPrivacy,
    required bool modelTrainingOptIn,
  }) => _authenticate('/auth/register', {
    'email': email,
    'password': password,
    'display_name': displayName,
    'accepted_terms': acceptedTerms,
    'accepted_privacy': acceptedPrivacy,
    'model_training_opt_in': modelTrainingOptIn,
  });

  @override
  Future<UserProfile> updateConsent({
    required bool acceptedTerms,
    required bool acceptedPrivacy,
    required bool modelTrainingOptIn,
  }) async {
    final data = await _api.request(
      'PUT',
      '/auth/consent',
      body: {
        'accepted_terms': acceptedTerms,
        'accepted_privacy': acceptedPrivacy,
        'model_training_opt_in': modelTrainingOptIn,
      },
    );
    await _api.saveCachedUser(data);
    return UserProfile.fromJson(data);
  }

  @override
  Future<UserProfile> updateUsername(String username) async {
    final data = await _api.request(
      'PUT',
      '/auth/profile',
      body: {'username': username.trim()},
    );
    await _api.saveCachedUser(data);
    return UserProfile.fromJson(data);
  }

  @override
  Future<UserProfile> completeOnboarding({required bool skipped}) async {
    final data = await _api.request(
      'PUT',
      '/auth/onboarding',
      body: {'action': skipped ? 'skipped' : 'completed'},
    );
    await _api.saveCachedUser(data);
    return UserProfile.fromJson(data);
  }

  Future<UserProfile> _authenticate(
    String path,
    Map<String, dynamic> body,
  ) async {
    final data = await _api.request(
      'POST',
      path,
      body: body,
      authenticated: false,
    );
    await _api.saveToken(data['access_token'] as String);
    final user = data['user'] as Map<String, dynamic>;
    await _api.saveCachedUser(user);
    return UserProfile.fromJson(user);
  }

  @override
  Future<void> logout() => _api.clearToken();

  @override
  Future<List<TransactionRecord>> transactions() async {
    final records = <TransactionRecord>[];
    var page = 1;
    while (true) {
      final data = await _api.request(
        'GET',
        '/transactions?per_page=100&page=$page',
      );
      final items = (data['items'] as List<dynamic>)
          .cast<Map<String, dynamic>>();
      records.addAll(items.map(TransactionRecord.fromJson));
      final total = data['total'] as int? ?? records.length;
      if (items.isEmpty || records.length >= total) break;
      page += 1;
    }
    return List<TransactionRecord>.unmodifiable(records);
  }

  @override
  Future<TransactionRecord> addTransaction({
    required DateTime timestamp,
    required double amount,
    required String category,
    required String transactionType,
    String? merchant,
    bool isRecurring = false,
  }) async {
    final data = await _api.request(
      'POST',
      '/transactions',
      body: {
        'transaction_timestamp': timestamp.toUtc().toIso8601String(),
        'amount': amount,
        'category': category,
        'transaction_type': transactionType,
        'merchant': merchant,
        'is_recurring': isRecurring,
      },
    );
    return TransactionRecord.fromJson(data);
  }

  @override
  Future<void> deleteTransaction(String id) async {
    await _api.request('DELETE', '/transactions/$id');
  }

  @override
  Future<TransactionRecord> transaction(String id) async =>
      TransactionRecord.fromJson(
        await _api.request('GET', '/transactions/${Uri.encodeComponent(id)}'),
      );

  @override
  Future<AlertResult> reviewAlert(
    String id, {
    required bool intentional,
    required String transactionReviewVersion,
  }) async => AlertResult.fromJson(
    await _api.request(
      'PUT',
      '/alerts/${Uri.encodeComponent(id)}/review',
      body: {
        'status': intentional ? 'intentional' : 'pending',
        'transaction_review_version': transactionReviewVersion,
      },
    ),
  );

  Map<String, dynamic> _transactionBody({
    required DateTime timestamp,
    required double amount,
    required String category,
    required String transactionType,
    String? merchant,
    bool isRecurring = false,
  }) => {
    'transaction_timestamp': timestamp.toUtc().toIso8601String(),
    'amount': amount,
    'category': category,
    'transaction_type': transactionType,
    'merchant': merchant,
    'is_recurring': isRecurring,
  };

  @override
  Future<TransactionRecord> updateTransaction({
    required String id,
    required DateTime timestamp,
    required double amount,
    required String category,
    required String transactionType,
    String? merchant,
    bool isRecurring = false,
  }) async {
    final data = await _api.request(
      'PUT',
      '/transactions/$id',
      body: _transactionBody(
        timestamp: timestamp,
        amount: amount,
        category: category,
        transactionType: transactionType,
        merchant: merchant,
        isRecurring: isRecurring,
      ),
    );
    return TransactionRecord.fromJson(data);
  }

  @override
  Future<Map<String, dynamic>> uploadTransactions(String filePath) =>
      _api.uploadCsv(filePath);

  @override
  Future<List<BudgetRecord>> budgets() async {
    final data = await _api.request('GET', '/budgets');
    return (data['items'] as List<dynamic>)
        .cast<Map<String, dynamic>>()
        .map(BudgetRecord.fromJson)
        .toList(growable: false);
  }

  @override
  Future<BudgetRecord> createBudget({
    required DateTime periodStart,
    required DateTime periodEnd,
    required String category,
    required double amount,
  }) async {
    final data = await _api.request(
      'POST',
      '/budgets',
      body: {
        'period_start': periodStart.toIso8601String().split('T').first,
        'period_end': periodEnd.toIso8601String().split('T').first,
        'category': category,
        'amount': amount,
      },
    );
    return BudgetRecord.fromJson(data);
  }

  Map<String, dynamic> _budgetBody({
    required DateTime periodStart,
    required DateTime periodEnd,
    required String category,
    required double amount,
  }) => {
    'period_start': periodStart.toIso8601String().split('T').first,
    'period_end': periodEnd.toIso8601String().split('T').first,
    'category': category,
    'amount': amount,
  };

  @override
  Future<BudgetRecord> updateBudget({
    required String id,
    required DateTime periodStart,
    required DateTime periodEnd,
    required String category,
    required double amount,
  }) async {
    final data = await _api.request(
      'PUT',
      '/budgets/$id',
      body: _budgetBody(
        periodStart: periodStart,
        periodEnd: periodEnd,
        category: category,
        amount: amount,
      ),
    );
    return BudgetRecord.fromJson(data);
  }

  @override
  Future<void> deleteBudget(String id) async {
    await _api.request('DELETE', '/budgets/$id');
  }

  @override
  Future<CashflowAnalytics> cashflowAnalytics(String resolution) async {
    final data = await _api.request(
      'GET',
      '/analytics/cashflow?resolution=${Uri.encodeQueryComponent(resolution)}',
    );
    return CashflowAnalytics.fromJson(data);
  }

  @override
  Future<DashboardSummary> dashboardSummary(String period) async {
    final data = await _api.request(
      'GET',
      '/analytics/dashboard?period=${Uri.encodeQueryComponent(period)}',
    );
    return DashboardSummary.fromJson(data);
  }

  @override
  Future<AnalysisResult> runAnalysis({DateTime? historyCompleteFrom}) async {
    final data = await _api.request(
      'POST',
      '/analysis/run',
      body: {
        'use_stored_transactions': true,
        if (historyCompleteFrom != null)
          'history_complete_from':
              '${historyCompleteFrom.year.toString().padLeft(4, '0')}-${historyCompleteFrom.month.toString().padLeft(2, '0')}-${historyCompleteFrom.day.toString().padLeft(2, '0')}',
      },
    );
    return AnalysisResult.fromJson(data);
  }

  @override
  Future<AnalysisResult> latestAnalysis() async {
    final data = await _api.request('GET', '/analysis/latest');
    return AnalysisResult.fromJson(data);
  }

  @override
  Future<List<Map<String, dynamic>>> history(String resource) async {
    final data = await _api.request('GET', '/$resource?per_page=100');
    return (data['items'] as List<dynamic>).cast<Map<String, dynamic>>().toList(
      growable: false,
    );
  }
}
