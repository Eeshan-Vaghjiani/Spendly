import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/data/services/google_identity_service.dart';
import 'package:spending_support/domain/repositories/spending_repository.dart';
import 'package:spending_support/main.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/alert_screen.dart';
import 'package:spending_support/presentation/screens/recommendations_screen.dart';

class FakeRepository implements SpendingRepository {
  FakeRepository({this.restoredUser, this.newAccountsNeedOnboarding = false});

  final UserProfile? restoredUser;
  final bool newAccountsNeedOnboarding;
  final createdBudgets = <BudgetRecord>[];
  final createdTransactions = <TransactionRecord>[];
  int transactionListCalls = 0;
  int dashboardSummaryCalls = 0;
  final user = const UserProfile(
    id: 'user-1',
    email: 'eva@example.com',
    displayName: 'Eva',
    username: 'eva',
  );

  AnalysisResult get analysis => AnalysisResult(
    id: 'analysis-1',
    generatedAt: DateTime.utc(2026, 7, 25),
    forecast: ForecastResult(
      modelVersion: 'v1',
      periodStart: DateTime.utc(2026, 7, 27),
      periodEnd: DateTime.utc(2026, 8, 2),
      predictedSpending: 12000,
      baselinePrediction: 11500,
    ),
    alerts: const [
      AlertResult(
        isUnusualSpending: true,
        anomalyScore: 0.1,
        explanation: 'Review an unusual transaction.',
      ),
    ],
    recommendations: const [
      RecommendationResult(
        code: 'FORECAST_EXCEEDS_BUDGET',
        title: 'Forecast is above budget',
        message: 'Review next week’s planned spending.',
        severity: 'high',
        reason: 'Forecast is greater than budget.',
        suggestedAction: 'Review the largest categories.',
        disclaimer: 'Decision support only.',
      ),
    ],
  );

  @override
  Future<UserProfile?> restoreSession() async => restoredUser;

  @override
  Future<UserProfile> login(String email, String password) async => user;

  @override
  Future<UserProfile> loginWithGoogle(String idToken) async =>
      newAccountsNeedOnboarding
      ? const UserProfile(
          id: 'user-1',
          email: 'eva@example.com',
          displayName: 'Eva',
          username: 'eva',
          onboardingCompleted: false,
        )
      : user;

  @override
  Future<UserProfile> register(
    String email,
    String password,
    String displayName, {
    required bool acceptedTerms,
    required bool acceptedPrivacy,
    required bool modelTrainingOptIn,
  }) async => newAccountsNeedOnboarding
      ? const UserProfile(
          id: 'user-1',
          email: 'eva@example.com',
          displayName: 'Eva',
          username: 'eva',
          onboardingCompleted: false,
        )
      : user;

  @override
  Future<UserProfile> updateConsent({
    required bool acceptedTerms,
    required bool acceptedPrivacy,
    required bool modelTrainingOptIn,
  }) async => newAccountsNeedOnboarding
      ? const UserProfile(
          id: 'user-1',
          email: 'eva@example.com',
          displayName: 'Eva',
          username: 'eva',
          onboardingCompleted: false,
        )
      : user;

  @override
  Future<UserProfile> updateUsername(String username) async => UserProfile(
    id: user.id,
    email: user.email,
    displayName: user.displayName,
    username: username.trim(),
  );

  @override
  Future<UserProfile> completeOnboarding({required bool skipped}) async => user;

  @override
  Future<void> logout() async {}

  @override
  Future<List<TransactionRecord>> transactions() async {
    transactionListCalls += 1;
    return List<TransactionRecord>.unmodifiable(createdTransactions);
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
    final transaction = TransactionRecord(
      id: 'transaction-1',
      timestamp: timestamp,
      amount: amount,
      category: category,
      transactionType: transactionType,
      merchant: merchant,
      isRecurring: isRecurring,
    );
    createdTransactions.add(transaction);
    return transaction;
  }

  @override
  Future<void> deleteTransaction(String id) async {}

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
    final transaction = TransactionRecord(
      id: id,
      timestamp: timestamp,
      amount: amount,
      category: category,
      transactionType: transactionType,
      merchant: merchant,
      isRecurring: isRecurring,
    );
    final index = createdTransactions.indexWhere((item) => item.id == id);
    if (index >= 0) createdTransactions[index] = transaction;
    return transaction;
  }

  @override
  Future<Map<String, dynamic>> uploadTransactions(String filePath) async => {
    'received_rows': 1,
    'created_rows': 1,
  };

  @override
  Future<List<BudgetRecord>> budgets() async =>
      List<BudgetRecord>.unmodifiable(createdBudgets);

  @override
  Future<BudgetRecord> createBudget({
    required DateTime periodStart,
    required DateTime periodEnd,
    required String category,
    required double amount,
  }) async {
    final budget = BudgetRecord(
      id: 'budget-1',
      periodStart: periodStart,
      periodEnd: periodEnd,
      category: category,
      amount: amount,
    );
    createdBudgets.add(budget);
    return budget;
  }

  @override
  Future<BudgetRecord> updateBudget({
    required String id,
    required DateTime periodStart,
    required DateTime periodEnd,
    required String category,
    required double amount,
  }) async {
    final budget = BudgetRecord(
      id: id,
      periodStart: periodStart,
      periodEnd: periodEnd,
      category: category,
      amount: amount,
    );
    final index = createdBudgets.indexWhere((item) => item.id == id);
    if (index >= 0) createdBudgets[index] = budget;
    return budget;
  }

  @override
  Future<void> deleteBudget(String id) async {
    createdBudgets.removeWhere((item) => item.id == id);
  }

  @override
  Future<CashflowAnalytics> cashflowAnalytics(String resolution) async {
    return CashflowAnalytics(
      resolution: resolution,
      periodStart: DateTime(2026, 1, 1),
      periodEnd: DateTime(2026, 12, 31),
      summary: const CashflowSummary(
        income: 50000,
        expense: 30000,
        net: 20000,
        cashBalance: 20000,
        savingsRate: 40,
        budgeted: 35000,
      ),
      series: [
        CashflowPoint(
          periodStart: DateTime(2026, 1, 1),
          periodEnd: DateTime(2026, 1, 31),
          label: 'Jan 2026',
          income: 50000,
          expense: 30000,
          net: 20000,
        ),
      ],
    );
  }

  @override
  Future<DashboardSummary> dashboardSummary(String period) async {
    dashboardSummaryCalls += 1;
    final expenses = createdTransactions
        .where((item) => item.transactionType == 'expense')
        .fold<double>(0, (sum, item) => sum + item.amount);
    final income = createdTransactions
        .where((item) => item.transactionType == 'income')
        .fold<double>(0, (sum, item) => sum + item.amount);
    final categories = <String, double>{};
    for (final transaction in createdTransactions.where(
      (item) => item.transactionType == 'expense',
    )) {
      categories.update(
        transaction.category,
        (value) => value + transaction.amount,
        ifAbsent: () => transaction.amount,
      );
    }
    final topCategory = categories.entries.isEmpty
        ? null
        : (categories.entries.toList()
                ..sort((a, b) => b.value.compareTo(a.value)))
              .first;
    return DashboardSummary(
      period: period,
      periodStart: DateTime(2026, 8, 1),
      periodEnd: DateTime(2026, 8, 25),
      transactionCount: createdTransactions.length,
      hasTransactions: createdTransactions.isNotEmpty,
      hasOlderTransactions: false,
      income: income,
      expense: expenses,
      net: income - expenses,
      cashBalance: income - expenses,
      topCategory: topCategory?.key,
      topCategoryAmount: topCategory?.value ?? 0,
      activeBudgetAmount: 0,
      activeBudgetSpent: 0,
      activeBudgetPercent: 0,
      hasActiveBudget: false,
    );
  }

  @override
  Future<AnalysisResult> runAnalysis() async => analysis;

  @override
  Future<AnalysisResult> latestAnalysis() async => analysis;

  @override
  Future<List<Map<String, dynamic>>> history(String resource) async => const [];
}

class FakeGoogleIdentity implements GoogleIdentityProvider {
  FakeGoogleIdentity({this.configured = false});

  final bool configured;

  @override
  bool get isConfigured => configured;

  @override
  Future<String> authenticate() async => 'test-google-id-token';

  @override
  Future<void> signOut() async {}
}

Widget appWith(
  FakeRepository repository, {
  GoogleIdentityProvider? googleIdentity,
}) => ProviderScope(
  overrides: [
    repositoryProvider.overrideWithValue(repository),
    googleIdentityProvider.overrideWithValue(
      googleIdentity ?? FakeGoogleIdentity(),
    ),
  ],
  child: const SpendlyApp(),
);

void main() {
  testWidgets('registration requires essential data consent', (tester) async {
    await tester.pumpWidget(
      appWith(FakeRepository(newAccountsNeedOnboarding: true)),
    );
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('register-display-name')),
      'Eva',
    );
    await tester.enterText(
      find.byKey(const Key('register-email')),
      'eva@example.com',
    );
    await tester.enterText(
      find.byKey(const Key('register-password')),
      'StrongPass123!',
    );
    await tester.ensureVisible(find.byKey(const Key('register-continue')));
    await tester.tap(find.byKey(const Key('register-continue')));
    await tester.pumpAndSettle();

    expect(find.text('Know what happens to your data'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const Key('accept-service-terms')),
      220,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.tap(find.byKey(const Key('accept-service-terms')));
    await tester.scrollUntilVisible(
      find.byKey(const Key('accept-privacy-use')),
      160,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.tap(find.byKey(const Key('accept-privacy-use')));
    await tester.scrollUntilVisible(
      find.byKey(const Key('complete-data-setup')),
      220,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.tap(find.byKey(const Key('complete-data-setup')));
    await tester.pumpAndSettle();

    expect(find.text('Welcome to Spendly'), findsOneWidget);
    await tester.tap(find.byKey(const Key('onboarding-skip')));
    await tester.pumpAndSettle();
    expect(find.text('Dashboard'), findsWidgets);
  });

  testWidgets('registration offers the same working Google action', (
    tester,
  ) async {
    await tester.pumpWidget(
      appWith(
        FakeRepository(),
        googleIdentity: FakeGoogleIdentity(configured: true),
      ),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('register-google')));
    expect(find.text('Continue with Google'), findsOneWidget);
    await tester.tap(find.byKey(const Key('register-google')));
    await tester.pumpAndSettle();
    expect(find.text('Dashboard'), findsWidgets);
  });

  testWidgets('new user can finish onboarding and returning user skips it', (
    tester,
  ) async {
    await tester.pumpWidget(
      appWith(
        FakeRepository(
          restoredUser: const UserProfile(
            id: 'new-user',
            email: 'new@example.com',
            displayName: 'New User',
            username: 'new_user',
            onboardingCompleted: false,
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Welcome to Spendly'), findsOneWidget);
    for (var page = 0; page < 3; page += 1) {
      await tester.tap(find.byKey(const Key('onboarding-next')));
      await tester.pumpAndSettle();
    }
    expect(find.text('Stay informed'), findsOneWidget);
    await tester.tap(find.byKey(const Key('onboarding-get-started')));
    await tester.pumpAndSettle();
    expect(find.text('Dashboard'), findsWidgets);

    await tester.pumpWidget(
      appWith(
        FakeRepository(
          restoredUser: const UserProfile(
            id: 'returning-user',
            email: 'returning@example.com',
            displayName: 'Returning User',
            username: 'returning_user',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Welcome to Spendly'), findsNothing);
    expect(find.text('Dashboard'), findsWidgets);
  });

  testWidgets(
    'onboarding supports keyboard navigation and accessible targets',
    (tester) async {
      final semantics = tester.ensureSemantics();
      await tester.pumpWidget(
        appWith(
          FakeRepository(
            restoredUser: const UserProfile(
              id: 'keyboard-user',
              email: 'keyboard@example.com',
              displayName: 'Keyboard User',
              username: 'keyboard_user',
              onboardingCompleted: false,
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.sendKeyEvent(LogicalKeyboardKey.arrowRight);
      await tester.pumpAndSettle();
      expect(find.text('Track your spending'), findsOneWidget);
      await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
      await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
      semantics.dispose();
    },
  );

  testWidgets('login opens the authenticated dashboard', (tester) async {
    await tester.pumpWidget(appWith(FakeRepository()));
    await tester.pumpAndSettle();
    expect(find.text('Create your account'), findsOneWidget);
    await tester.ensureVisible(find.text('Already have an account? Sign in'));
    await tester.tap(find.text('Already have an account? Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Welcome back'), findsOneWidget);
    await tester.enterText(
      find.byKey(const Key('login-email')),
      'eva@example.com',
    );
    await tester.enterText(
      find.byKey(const Key('login-password')),
      'StrongPass123!',
    );
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pumpAndSettle();
    expect(find.text('Dashboard'), findsWidgets);
    expect(find.text('Hello, eva'), findsOneWidget);
  });

  testWidgets('Google login exchanges identity for a Spendly session', (
    tester,
  ) async {
    await tester.pumpWidget(
      appWith(
        FakeRepository(),
        googleIdentity: FakeGoogleIdentity(configured: true),
      ),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Already have an account? Sign in'));
    await tester.tap(find.text('Already have an account? Sign in'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('login-google')));
    await tester.tap(find.byKey(const Key('login-google')));
    await tester.pumpAndSettle();
    expect(find.text('Dashboard'), findsWidgets);
  });

  testWidgets('dashboard displays forecast, alert, and recommendation result', (
    tester,
  ) async {
    await tester.pumpWidget(
      appWith(
        FakeRepository(
          restoredUser: const UserProfile(
            id: 'user-1',
            email: 'eva@example.com',
            displayName: 'Eva',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Next 7 days'),
      220,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.drag(find.byType(ListView).first, const Offset(0, -160));
    await tester.pumpAndSettle();
    expect(find.text('Next 7 days'), findsOneWidget);
    expect(find.text('1 item to review'), findsOneWidget);
    expect(find.text('Forecast is above budget'), findsOneWidget);
    await tester.tap(find.text('Next 7 days'));
    await tester.pumpAndSettle();
    expect(find.text('Learning progress'), findsOneWidget);
    expect(find.text('Week 8 of 8 · Established data'), findsOneWidget);
    expect(find.text('Accuracy pending'), findsOneWidget);
  });

  testWidgets('creating a budget closes the dialog without framework errors', (
    tester,
  ) async {
    await tester.pumpWidget(
      appWith(
        FakeRepository(
          restoredUser: const UserProfile(
            id: 'user-1',
            email: 'eva@example.com',
            displayName: 'Eva',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('Budgets').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Add budget'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('budget-amount')), '10000');
    await tester.tap(find.byKey(const Key('budget-create')));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.textContaining('10,000'), findsWidgets);
  });

  testWidgets('budget clearly warns when spending reaches 1411 percent', (
    tester,
  ) async {
    final repository = FakeRepository(
      restoredUser: const UserProfile(
        id: 'user-1',
        email: 'eva@example.com',
        displayName: 'Eva',
      ),
    );
    final now = DateTime.now();
    repository.createdBudgets.add(
      BudgetRecord(
        id: 'budget-over',
        periodStart: now.subtract(const Duration(days: 1)),
        periodEnd: now.add(const Duration(days: 1)),
        category: 'total',
        amount: 100,
      ),
    );
    repository.createdTransactions.add(
      TransactionRecord(
        id: 'expense-over',
        timestamp: now,
        amount: 1411,
        category: 'food',
        transactionType: 'expense',
        isRecurring: false,
      ),
    );

    await tester.pumpWidget(appWith(repository));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Budgets').last);
    await tester.pumpAndSettle();

    expect(find.text('1411% used'), findsOneWidget);
    expect(find.textContaining('Over budget by'), findsOneWidget);
    expect(find.text('Actually spent'), findsOneWidget);
    expect(find.text('Available to spend'), findsOneWidget);
  });

  testWidgets('dashboard refreshes when its navigation tab is reselected', (
    tester,
  ) async {
    final repository = FakeRepository(
      restoredUser: const UserProfile(
        id: 'user-1',
        email: 'eva@example.com',
        displayName: 'Eva',
      ),
    );
    await tester.pumpWidget(appWith(repository));
    await tester.pumpAndSettle();
    expect(find.text('KES 0'), findsWidgets);

    await tester.tap(find.text('Transactions').last);
    await tester.pumpAndSettle();
    await repository.addTransaction(
      timestamp: DateTime.now(),
      amount: 2500,
      category: 'food',
      transactionType: 'expense',
    );
    await tester.tap(find.text('Dashboard').last);
    await tester.pumpAndSettle();

    expect(find.text('KES 2,500'), findsWidgets);
    expect(find.text('food'), findsOneWidget);
  });

  testWidgets(
    'dashboard uses server summary, shows empty state, and keeps period',
    (tester) async {
      final repository = FakeRepository(
        restoredUser: const UserProfile(
          id: 'user-1',
          email: 'eva@example.com',
          displayName: 'Eva',
          username: 'eva',
        ),
      );
      await tester.pumpWidget(appWith(repository));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('dashboard-empty-period')), findsOneWidget);
      expect(repository.dashboardSummaryCalls, greaterThan(0));
      expect(repository.transactionListCalls, 0);

      await tester.tap(find.byKey(const Key('dashboard-period-weekly')));
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<ChoiceChip>(
              find.byKey(const Key('dashboard-period-weekly')),
            )
            .selected,
        isTrue,
      );
      await tester.tap(find.text('Transactions').last);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Dashboard').last);
      await tester.pumpAndSettle();
      expect(
        tester
            .widget<ChoiceChip>(
              find.byKey(const Key('dashboard-period-weekly')),
            )
            .selected,
        isTrue,
      );
    },
  );

  testWidgets('profile edits username and can replay introduction', (
    tester,
  ) async {
    await tester.pumpWidget(
      appWith(
        FakeRepository(
          restoredUser: const UserProfile(
            id: 'user-1',
            email: 'eva@example.com',
            displayName: 'Eva',
            username: 'eva',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('More').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('open-profile')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('edit-username')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('username-field')), findsOneWidget);
    expect(find.text('eva'), findsWidgets);
    await tester.enterText(
      find.byKey(const Key('username-field')),
      'eva_spends',
    );
    await tester.tap(find.byKey(const Key('save-username')));
    await tester.pumpAndSettle();
    expect(find.text('@eva_spends'), findsOneWidget);

    await tester.tap(find.byKey(const Key('replay-onboarding')));
    await tester.pumpAndSettle();
    expect(find.text('Welcome to Spendly'), findsOneWidget);
    await tester.tap(find.byKey(const Key('onboarding-skip')));
    await tester.pumpAndSettle();
    expect(find.text('Profile and settings'), findsOneWidget);
  });

  testWidgets('analytics tab provides time ranges and graph selection', (
    tester,
  ) async {
    await tester.pumpWidget(
      appWith(
        FakeRepository(
          restoredUser: const UserProfile(
            id: 'user-1',
            email: 'eva@example.com',
            displayName: 'Eva',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Analytics').last);
    await tester.pumpAndSettle();

    expect(find.text('Cash-flow trend'), findsOneWidget);
    expect(find.text('Daily'), findsOneWidget);
    expect(find.text('Weekly'), findsOneWidget);
    expect(find.text('Monthly'), findsOneWidget);
    expect(find.text('3 months'), findsOneWidget);
    expect(find.text('Yearly'), findsOneWidget);
    expect(find.text('Income + expense'), findsOneWidget);
    expect(find.text('Expenses'), findsOneWidget);
  });

  testWidgets('signing out returns to the login screen', (tester) async {
    await tester.pumpWidget(
      appWith(
        FakeRepository(
          restoredUser: const UserProfile(
            id: 'user-1',
            email: 'eva@example.com',
            displayName: 'Eva',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('More').last);
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('open-profile')));
    await tester.tap(find.byKey(const Key('open-profile')));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Sign out'),
      220,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.tap(find.text('Sign out'));
    await tester.pumpAndSettle();

    expect(find.text('Create your account'), findsOneWidget);
    expect(find.text('Sign out'), findsNothing);
  });

  testWidgets('recommendations show at most three focused actions', (
    tester,
  ) async {
    final recommendations = List.generate(
      4,
      (index) => RecommendationResult(
        code: 'STEP_$index',
        title: 'Helpful step ${index + 1}',
        message: 'Supporting message ${index + 1}',
        severity: index == 0 ? 'high' : 'info',
        reason: 'Supporting reason ${index + 1}',
        suggestedAction: 'Take action ${index + 1}.',
        disclaimer: 'Planning support only.',
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: RecommendationsScreen(recommendations: recommendations),
      ),
    );

    expect(find.text('Helpful step 1'), findsOneWidget);
    expect(find.text('Helpful step 4'), findsNothing);
    expect(find.text('Supporting reason 1'), findsNothing);
    await tester.tap(find.text('Why am I seeing this?').first);
    await tester.pumpAndSettle();
    expect(find.text('Supporting reason 1'), findsOneWidget);
  });

  testWidgets('spending check hides technical anomaly output', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: AlertScreen(
          alerts: [
            AlertResult(
              isUnusualSpending: true,
              explanation:
                  'Heuristic context from inputs: amount=42000, threshold=0.1.',
            ),
          ],
        ),
      ),
    );

    expect(
      find.text('This entry is different from what you usually record.'),
      findsOneWidget,
    );
    expect(find.textContaining('amount=42000'), findsNothing);
    expect(find.textContaining('threshold'), findsNothing);
  });
}
