import '../../data/models/models.dart';

abstract class SpendingRepository {
  Future<UserProfile?> restoreSession();
  Future<UserProfile> login(String email, String password);
  Future<UserProfile> loginWithGoogle(String idToken);
  Future<UserProfile> register(
    String email,
    String password,
    String displayName, {
    required bool acceptedTerms,
    required bool acceptedPrivacy,
    required bool modelTrainingOptIn,
  });
  Future<UserProfile> updateConsent({
    required bool acceptedTerms,
    required bool acceptedPrivacy,
    required bool modelTrainingOptIn,
  });
  Future<UserProfile> updateUsername(String username);
  Future<UserProfile> completeOnboarding({required bool skipped});
  Future<void> logout();
  Future<List<TransactionRecord>> transactions();
  Future<TransactionRecord> addTransaction({
    required DateTime timestamp,
    required double amount,
    required String category,
    required String transactionType,
    String? merchant,
    bool isRecurring = false,
  });
  Future<void> deleteTransaction(String id);
  Future<TransactionRecord> updateTransaction({
    required String id,
    required DateTime timestamp,
    required double amount,
    required String category,
    required String transactionType,
    String? merchant,
    bool isRecurring = false,
  });
  Future<Map<String, dynamic>> uploadTransactions(String filePath);
  Future<List<BudgetRecord>> budgets();
  Future<BudgetRecord> createBudget({
    required DateTime periodStart,
    required DateTime periodEnd,
    required String category,
    required double amount,
  });
  Future<BudgetRecord> updateBudget({
    required String id,
    required DateTime periodStart,
    required DateTime periodEnd,
    required String category,
    required double amount,
  });
  Future<void> deleteBudget(String id);
  Future<CashflowAnalytics> cashflowAnalytics(String resolution);
  Future<DashboardSummary> dashboardSummary(String period);
  Future<AnalysisResult> runAnalysis();
  Future<AnalysisResult> latestAnalysis();
  Future<List<Map<String, dynamic>>> history(String resource);
}
