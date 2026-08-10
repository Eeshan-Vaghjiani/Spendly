import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/data/repositories/api_spending_repository.dart';
import 'package:spending_support/data/services/api_client.dart';
import 'package:spending_support/data/services/token_store.dart';

class LiveMemoryTokenStore implements TokenStore {
  String? token;
  String? userJson;

  @override
  Future<void> clear() async {
    token = null;
    userJson = null;
  }

  @override
  Future<String?> read() async => token;

  @override
  Future<String?> readUser() async => userJson;

  @override
  Future<void> write(String token) async => this.token = token;

  @override
  Future<void> writeUser(String userJson) async => this.userJson = userJson;
}

void main() {
  const baseUrl = String.fromEnvironment('LIVE_API_BASE_URL');

  test('Flutter API layer completes the live Flask vertical slice', () async {
    if (baseUrl.isEmpty) {
      markTestSkipped(
        'Set LIVE_API_BASE_URL to execute the live backend integration test.',
      );
      return;
    }
    final repository = ApiSpendingRepository(
      ApiClient(baseUrl: baseUrl, tokenStore: LiveMemoryTokenStore()),
    );
    final email =
        'flutter-live-${DateTime.now().microsecondsSinceEpoch}@example.com';
    final user = await repository.register(
      email,
      'StrongPass123!',
      'Flutter Live Test',
      acceptedTerms: true,
      acceptedPrivacy: true,
      modelTrainingOptIn: false,
    );
    expect(user.email, email);

    final start = DateTime.utc(2026, 1, 5, 9);
    for (var week = 0; week < 8; week += 1) {
      final timestamp = start.add(Duration(days: week * 7));
      await repository.addTransaction(
        timestamp: timestamp,
        amount: week == 7 ? 100000 : 1000 + week * 50,
        category: 'food',
        transactionType: 'expense',
        merchant: 'Flutter Shop $week',
      );
      await repository.addTransaction(
        timestamp: timestamp.add(const Duration(hours: 1)),
        amount: 20000,
        category: 'salary',
        transactionType: 'income',
        merchant: 'Flutter Employer',
        isRecurring: true,
      );
    }
    await repository.createBudget(
      periodStart: DateTime.utc(2026, 3, 2),
      periodEnd: DateTime.utc(2026, 3, 8),
      category: 'total',
      amount: 15000,
    );
    final result = await repository.runAnalysis();
    expect(result.forecast.predictedSpending, greaterThanOrEqualTo(0));
    expect(result.forecast.modelVersion, 'v1');
    expect(result.alerts, isNotEmpty);
    expect(result.recommendations, isNotEmpty);
  });
}
