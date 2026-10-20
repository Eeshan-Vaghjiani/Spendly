import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:spending_support/core/network/api_exception.dart';
import 'package:spending_support/core/reporting_time.dart';
import 'package:spending_support/core/theme/app_theme.dart';
import 'package:spending_support/data/repositories/api_spending_repository.dart';
import 'package:spending_support/data/services/api_client.dart';
import 'package:spending_support/data/services/google_identity_service.dart';
import 'package:spending_support/data/services/token_store.dart';
import 'package:spending_support/main.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/dashboard_screen.dart';
import 'package:spending_support/presentation/screens/transaction_entry_screen.dart';
import 'package:spending_support/presentation/screens/transaction_upload_screen.dart';
import 'package:spending_support/presentation/screens/budget_screen.dart';
import 'package:spending_support/presentation/screens/analytics_screen.dart';
import 'package:spending_support/presentation/screens/analysis_history_screen.dart';
import 'package:spending_support/presentation/screens/forecast_detail_screen.dart';
import 'package:spending_support/presentation/screens/alert_screen.dart';
import 'package:spending_support/presentation/screens/recommendations_screen.dart';
import 'package:spending_support/presentation/screens/profile_screen.dart';
import 'package:spending_support/presentation/screens/more_screen.dart';
import 'package:spending_support/presentation/screens/transaction_history_screen.dart';

// Native OAuth is deliberately outside this synthetic-account suite.
class _SyntheticIdentity implements GoogleIdentityProvider {
  @override
  bool get isConfigured => false;
  @override
  Future<String> authenticate() =>
      throw UnsupportedError('Synthetic test does not use Google OAuth.');
  @override
  Future<void> signOut() async {}
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  const baseUrl = String.fromEnvironment('ACCEPTANCE_API_BASE_URL');

  testWidgets(
    'native storage, real local API, partial insights and account isolation',
    (tester) async {
      final uri = Uri.tryParse(baseUrl);
      if (uri == null ||
          !['127.0.0.1', '10.0.2.2'].contains(uri.host) ||
          uri.scheme != 'http' ||
          uri.port != 5057 ||
          uri.path != '/api/v1') {
        throw StateError(
          'Use the disposable loopback acceptance backend explicitly.',
        );
      }
      final package = await PackageInfo.fromPlatform();
      if (package.packageName !=
          'com.evagh.capstone.spending_support.acceptance') {
        throw StateError(
          'This suite can run only in the separate acceptance package.',
        );
      }
      final storage = SecureTokenStore();
      final api = ApiClient(baseUrl: baseUrl, tokenStore: storage);
      final target = await api.request('GET', '/acceptance-target');
      if (target['disposable'] != true || target['database'] != 'in_memory') {
        throw StateError(
          'Backend did not attest an in-memory disposable target.',
        );
      }
      final today = calendarDate(
        DateTime.parse(target['reporting_date'] as String),
      );
      await storage.clear();
      final repository = ApiSpendingRepository(api);
      final stamp = DateTime.now().microsecondsSinceEpoch;
      const password = 'SyntheticNativeOnly123!';
      final alpha = await repository.register(
        'native-alpha-$stamp@example.invalid',
        password,
        'Native Alpha',
        acceptedTerms: true,
        acceptedPrivacy: true,
        modelTrainingOptIn: false,
      );
      await repository.completeOnboarding(skipped: true);
      await repository.addTransaction(
        timestamp: today.add(const Duration(hours: 12)),
        amount: 125.50,
        category: 'food',
        transactionType: 'expense',
        merchant: 'Synthetic shop',
      );
      await expectLater(
        repository.addTransaction(
          timestamp: today.add(const Duration(hours: 12)),
          amount: .001,
          category: 'food',
          transactionType: 'expense',
        ),
        throwsA(
          isA<ApiException>().having(
            (error) => error.statusCode,
            'invalid money',
            422,
          ),
        ),
      );
      expect((await repository.transactions()).length, 1);
      await repository.createBudget(
        periodStart: today,
        periodEnd: today,
        category: 'total',
        amount: 200,
      );
      final snapshot = await repository.dashboardSummary('all_time');
      expect(snapshot.expense, 125.50);
      final partial = await repository.runAnalysis();
      expect(partial.forecast, isNull);
      expect(partial.forecastUnavailableMessage, isNotEmpty);
      expect(partial.recommendations, isNotEmpty);
      expect((await repository.restoreSession())?.id, alpha.id);

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            repositoryProvider.overrideWithValue(repository),
            googleIdentityProvider.overrideWithValue(_SyntheticIdentity()),
          ],
          child: const SpendlyApp(),
        ),
      );
      await tester.pumpAndSettle(
        const Duration(milliseconds: 200),
        EnginePhase.sendSemanticsUpdate,
        const Duration(seconds: 45),
      );
      expect(find.byType(DashboardScreen), findsOneWidget);
      await tester.scrollUntilVisible(
        find.byKey(const Key('forecast-unavailable')),
        250,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('Weekly estimate unavailable'), findsOneWidget);
      await tester.tap(find.text('Budgets').last);
      await tester.pumpAndSettle();
      expect(find.textContaining('125.50'), findsWidgets);
      await tester.tap(find.text('Add budget'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const Key('budget-amount')), 'NaN');
      await tester.tap(find.byKey(const Key('budget-create')));
      await tester.pumpAndSettle();
      expect(
        find.text('Enter an amount greater than zero and a category.'),
        findsOneWidget,
      );
      expect((await repository.budgets()).length, 1);
      await tester.enterText(find.byKey(const Key('budget-amount')), '500');
      await tester.enterText(
        find.byKey(const Key('budget-category')),
        'transport',
      );
      await tester.tap(find.byKey(const Key('budget-create')));
      await tester.tap(find.byKey(const Key('budget-create')));
      await tester.pumpAndSettle();
      expect((await repository.budgets()).length, 2);

      final navigator = tester.state<NavigatorState>(
        find.byType(Navigator).first,
      );
      final created = navigator.push<bool>(
        MaterialPageRoute(builder: (_) => const TransactionEntryScreen()),
      );
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('transaction-category')),
        'transport',
      );
      await tester.enterText(
        find.byKey(const Key('transaction-amount')),
        'NaN',
      );
      await tester.ensureVisible(find.byKey(const Key('transaction-save')));
      await tester.tap(find.byKey(const Key('transaction-save')));
      await tester.pumpAndSettle();
      expect(find.text('Enter an amount greater than zero.'), findsOneWidget);
      expect((await repository.transactions()).length, 1);
      await tester.enterText(
        find.byKey(const Key('transaction-amount')),
        '75.25',
      );
      await tester.ensureVisible(find.byKey(const Key('transaction-save')));
      await tester.tap(find.byKey(const Key('transaction-save')));
      await tester.tap(find.byKey(const Key('transaction-save')));
      await tester.pumpAndSettle();
      expect(await created, true);
      final records = await repository.transactions();
      expect(records.length, 2);
      final added = records.singleWhere(
        (record) => record.category == 'transport',
      );
      expect(added.amount, 75.25);
      final edited = navigator.push<bool>(
        MaterialPageRoute(
          builder: (_) => TransactionEntryScreen(transaction: added),
        ),
      );
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('transaction-amount')),
        '80.50',
      );
      await tester.ensureVisible(find.byKey(const Key('transaction-save')));
      await tester.tap(find.byKey(const Key('transaction-save')));
      await tester.pumpAndSettle();
      expect(await edited, true);
      expect((await repository.transaction(added.id)).amount, 80.50);
      final container = ProviderScope.containerOf(
        tester.element(find.byType(SpendlyApp)),
      );
      await container.read(authControllerProvider.notifier).logout();
      await tester.pumpAndSettle();
      expect(await storage.read(), isNull);
      expect(await repository.restoreSession(), isNull);
      expect(container.read(analysisControllerProvider).result, isNull);

      final betaEmail = 'native-beta-$stamp@example.invalid';
      final beta = await repository.register(
        betaEmail,
        password,
        'Native Beta',
        acceptedTerms: true,
        acceptedPrivacy: true,
        modelTrainingOptIn: false,
      );
      await repository.completeOnboarding(skipped: true);
      expect(
        await container
            .read(authControllerProvider.notifier)
            .login(betaEmail, password),
        true,
      );
      await tester.pumpAndSettle();
      expect(container.read(authControllerProvider).user?.id, beta.id);
      expect((await repository.dashboardSummary('all_time')).expense, 0);
      expect(await repository.transactions(), isEmpty);
      await container.read(analysisControllerProvider.notifier).run();
      await tester.pumpAndSettle();
      final betaResult = container.read(analysisControllerProvider).result;
      expect(betaResult, isNotNull);
      expect(betaResult?.id, isNot(partial.id));
      expect(betaResult?.forecast, isNull);
      expect(container.read(analysisControllerProvider).error, isNull);
      // Fully controlled synthetic coverage: all eight preceding weeks are known.
      final targetWeek = today.subtract(Duration(days: today.weekday - 1));
      final historyStart = targetWeek.subtract(const Duration(days: 56));
      for (var week = 1; week <= 8; week++) {
        await repository.addTransaction(
          timestamp: targetWeek
              .subtract(Duration(days: week * 7))
              .add(const Duration(hours: 12)),
          amount: 100 + week * 10,
          category: 'food',
          transactionType: 'expense',
          merchant: 'Synthetic history',
        );
      }
      final controller = container.read(analysisControllerProvider.notifier);
      controller.historyCompleteFrom = historyStart;
      await controller.run();
      await tester.pumpAndSettle();
      final estimate = container
          .read(analysisControllerProvider)
          .result
          ?.forecast;
      expect(estimate, isNotNull);
      expect(calendarDate(estimate!.periodStart), targetWeek);
      expect(estimate.predictedSpending.isFinite, true);
      expect(estimate.predictedSpending, greaterThanOrEqualTo(0));
      final result = container.read(analysisControllerProvider).result!;
      final pages = <String, Widget>{
        'dashboard': const DashboardScreen(),
        'transactions': const TransactionHistoryScreen(),
        'budgets': const BudgetScreen(),
        'analytics': const AnalyticsScreen(),
        'history': const AnalysisHistoryScreen(),
        'forecast': ForecastDetailScreen(forecast: estimate),
        'spending check': AlertScreen(alerts: result.alerts),
        'recommendations': RecommendationsScreen(
          recommendations: result.recommendations,
        ),
        'profile': const ProfileScreen(),
        'more': const MoreScreen(),
        'upload': const TransactionUploadScreen(),
      };
      for (final entry in pages.entries) {
        navigator.push<void>(
          MaterialPageRoute(
            builder: (context) => MediaQuery(
              data: MediaQuery.of(
                context,
              ).copyWith(textScaler: const TextScaler.linear(2)),
              child: entry.value,
            ),
          ),
        );
        await tester.pumpAndSettle(
          const Duration(milliseconds: 200),
          EnginePhase.sendSemanticsUpdate,
          const Duration(seconds: 45),
        );
        expect(tester.takeException(), isNull, reason: entry.key);
        final vertical = find.byWidgetPredicate(
          (widget) =>
              widget is Scrollable &&
              widget.axisDirection == AxisDirection.down,
        );
        if (vertical.evaluate().isNotEmpty) {
          for (var step = 0; step < 30; step++) {
            if (tester
                    .state<ScrollableState>(vertical.first)
                    .position
                    .extentAfter <=
                0) {
              break;
            }
            await tester.drag(vertical.first, const Offset(0, -450));
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull, reason: entry.key);
          }
          expect(
            tester.state<ScrollableState>(vertical.first).position.extentAfter,
            0,
            reason: entry.key,
          );
        }
        debugPrint('SPENDLY_PAGE_REVIEW:${entry.key}:200pct:passed');
        navigator.pop();
        await tester.pumpAndSettle();
      }
      await container.read(authControllerProvider.notifier).logout();
      await tester.pumpAndSettle();
      expect(await storage.read(), isNull);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets(
    'native CSV picker cancellation, import, duplicate recovery and large text',
    (tester) async {
      final uri = Uri.tryParse(baseUrl);
      if (uri == null ||
          uri.scheme != 'http' ||
          !['127.0.0.1', '10.0.2.2'].contains(uri.host) ||
          uri.port != 5057 ||
          uri.path != '/api/v1') {
        throw StateError('Use the disposable loopback acceptance backend.');
      }
      final package = await PackageInfo.fromPlatform();
      if (package.packageName !=
          'com.evagh.capstone.spending_support.acceptance') {
        throw StateError('The separate acceptance package is required.');
      }
      final storage = SecureTokenStore();
      final api = ApiClient(baseUrl: baseUrl, tokenStore: storage);
      final target = await api.request('GET', '/acceptance-target');
      if (target['disposable'] != true || target['database'] != 'in_memory') {
        throw StateError('Backend must attest a disposable in-memory target.');
      }
      await storage.clear();
      final repository = ApiSpendingRepository(api);
      final stamp = DateTime.now().microsecondsSinceEpoch;
      await repository.register(
        'native-import-$stamp@example.invalid',
        'SyntheticNativeOnly123!',
        'Synthetic Import',
        acceptedTerms: true,
        acceptedPrivacy: true,
        modelTrainingOptIn: false,
      );
      addTearDown(repository.logout);
      await repository.completeOnboarding(skipped: true);
      await tester.pumpWidget(
        ProviderScope(
          overrides: [repositoryProvider.overrideWithValue(repository)],
          child: MaterialApp(
            theme: AppTheme.light(),
            home: const PopScope(
              canPop: false,
              child: TransactionUploadScreen(),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      Future<void> choose(String phase) async {
        await tester.tap(find.text('Choose CSV file'));
        await tester.pump();
        debugPrint('SPENDLY_PICKER:$phase');
        final deadline = DateTime.now().add(const Duration(minutes: 2));
        while (tester
                .widget<FilledButton>(find.byType(FilledButton))
                .onPressed ==
            null) {
          if (DateTime.now().isAfter(deadline)) {
            throw StateError('Native picker driver timed out: $phase');
          }
          await tester.pump(const Duration(milliseconds: 250));
        }
        await tester.pumpAndSettle();
      }

      Future<void> summary(String label, int count) async {
        final row = find.ancestor(
          of: find.text(label),
          matching: find.byType(ListTile),
        );
        expect(
          find.descendant(of: row, matching: find.text('$count')),
          findsOneWidget,
        );
      }

      await choose('cancel');
      expect(await repository.transactions(), isEmpty);
      expect(find.text('Upload summary'), findsNothing);
      await choose('mixed');
      await summary('Rows received', 4);
      await summary('Rows created', 2);
      await summary('Duplicates', 1);
      await summary('Invalid rows', 1);
      expect((await repository.transactions()).length, 2);
      await choose('repeat');
      await summary('Rows created', 0);
      await summary('Duplicates', 3);
      await summary('Invalid rows', 1);
      expect((await repository.transactions()).length, 2);
      await choose('invalid');
      expect(find.text('Upload summary'), findsNothing);
      expect(find.text('The CSV is missing required columns.'), findsOneWidget);
      expect((await repository.transactions()).length, 2);
      await choose('recover');
      await summary('Rows created', 0);
      await summary('Duplicates', 3);
      expect((await repository.transactions()).length, 2);

      final today = calendarDate(
        DateTime.parse(target['reporting_date'] as String),
      );
      await repository.createBudget(
        periodStart: today,
        periodEnd: today,
        category: 'total',
        amount: 1250000,
      );
      await repository.addTransaction(
        timestamp: today.add(const Duration(hours: 12)),
        amount: 1500000,
        category: 'food',
        transactionType: 'expense',
        merchant: 'Synthetic large-text shop',
      );
      await tester.pumpWidget(
        ProviderScope(
          overrides: [repositoryProvider.overrideWithValue(repository)],
          child: MaterialApp(
            theme: AppTheme.light(),
            builder: (context, child) => MediaQuery(
              data: MediaQuery.of(
                context,
              ).copyWith(textScaler: TextScaler.linear(2)),
              child: child!,
            ),
            home: const BudgetScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      expect(find.text('KES 1,500,000.00 of KES 1,250,000.00'), findsOneWidget);
      await tester.tap(find.byTooltip('Budget actions'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Edit'));
      await tester.pumpAndSettle();
      expect(find.text('1250000.00'), findsOneWidget);
      expect(tester.takeException(), isNull);
      debugPrint('SPENDLY_NATIVE_IMPORT:passed');
    },
    skip: !const bool.fromEnvironment('NATIVE_PICKER_ACCEPTANCE'),
  );
}
