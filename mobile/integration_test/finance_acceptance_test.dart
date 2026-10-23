import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:integration_test/integration_test.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:spending_support/core/reporting_time.dart';
import 'package:spending_support/core/theme/app_theme.dart';
import 'package:spending_support/data/repositories/api_spending_repository.dart';
import 'package:spending_support/data/services/api_client.dart';
import 'package:spending_support/data/services/token_store.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/analytics_screen.dart';
import 'package:spending_support/presentation/screens/budget_screen.dart';
import 'package:spending_support/presentation/screens/dashboard_screen.dart';
import 'package:spending_support/presentation/screens/transaction_history_screen.dart';

// Uses actual Android HTTP sockets. Failure mode targets a just-closed port on
// this disposable emulator, never a hosted API or the user's network settings.
class _ConnectionSwitch extends http.BaseClient {
  _ConnectionSwitch(this.closedPort);
  final int closedPort;
  final _inner = http.Client();
  bool disconnected = false;
  int failedWrites = 0;
  final analyticsResolutions = <String>[];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    if (!disconnected) {
      if (request.url.path.endsWith('/analytics/cashflow')) {
        analyticsResolutions.add(request.url.queryParameters['resolution']!);
      }
      return _inner.send(request);
    }
    if (request is! http.Request) {
      throw StateError('Only JSON requests belong in this acceptance suite.');
    }
    if (request.method != 'GET') failedWrites++;
    final unavailable =
        http.Request(
            request.method,
            request.url.replace(host: '127.0.0.1', port: closedPort),
          )
          ..headers.addAll(request.headers)
          ..bodyBytes = request.bodyBytes;
    return _inner.send(unavailable);
  }

  @override
  void close() => _inner.close();
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  const baseUrl = String.fromEnvironment('ACCEPTANCE_API_BASE_URL');

  testWidgets('native budget CRUD, filters and socket-failure recovery', (
    tester,
  ) async {
    final uri = Uri.tryParse(baseUrl);
    if (uri == null ||
        uri.scheme != 'http' ||
        !['127.0.0.1', '10.0.2.2'].contains(uri.host) ||
        uri.port != 5057 ||
        uri.path != '/api/v1') {
      throw StateError(
        'Use the disposable loopback acceptance API explicitly.',
      );
    }
    if ((await PackageInfo.fromPlatform()).packageName !=
        'com.evagh.capstone.spending_support.acceptance') {
      throw StateError('Run only in the separate acceptance package.');
    }
    final reservation = await ServerSocket.bind(
      InternetAddress.loopbackIPv4,
      0,
    );
    final transport = _ConnectionSwitch(reservation.port);
    await reservation.close();
    final storage = SecureTokenStore();
    final api = ApiClient(
      baseUrl: baseUrl,
      tokenStore: storage,
      httpClient: transport,
      requestTimeout: const Duration(seconds: 5),
    );
    addTearDown(api.close);
    final target = await api.request(
      'GET',
      '/acceptance-target',
      authenticated: false,
    );
    if (target['disposable'] != true || target['database'] != 'in_memory') {
      throw StateError('Backend must attest an in-memory disposable target.');
    }
    addTearDown(() async {
      transport.disconnected = false;
      await storage.clear();
    });
    await storage.clear();
    final repository = ApiSpendingRepository(api);
    await repository.register(
      'native-finance-${DateTime.now().microsecondsSinceEpoch}@example.invalid',
      'SyntheticFinanceOnly123!',
      'Native finance fixture',
      acceptedTerms: true,
      acceptedPrivacy: true,
      modelTrainingOptIn: false,
    );
    await repository.completeOnboarding(skipped: true);
    final today = calendarDate(
      DateTime.parse(target['reporting_date'] as String),
    );

    Future<void> settle() async {
      await tester.pumpAndSettle(
        const Duration(milliseconds: 200),
        EnginePhase.sendSemanticsUpdate,
        const Duration(seconds: 30),
      );
      expect(tester.takeException(), isNull);
    }

    Future<void> show(Widget screen) async {
      await tester.pumpWidget(
        ProviderScope(
          key: UniqueKey(),
          overrides: [repositoryProvider.overrideWithValue(repository)],
          child: MaterialApp(theme: AppTheme.light(), home: screen),
        ),
      );
      await settle();
    }

    Future<void> tap(Finder finder) async {
      await tester.ensureVisible(finder);
      await tester.tap(finder);
      await settle();
    }

    Future<void> budgetAction(String action) async {
      await tap(find.byTooltip('Budget actions'));
      await tap(find.text(action));
    }

    await show(const BudgetScreen());
    expect(find.text('No budget is configured.'), findsOneWidget);
    await tap(find.text('Add budget'));
    await tester.enterText(find.byKey(const Key('budget-amount')), '500');
    await tester.enterText(
      find.byKey(const Key('budget-category')),
      'transport',
    );
    await tap(find.byKey(const Key('budget-create')));
    final budget = (await repository.budgets()).single;
    expect(budget.amount, 500);
    await budgetAction('Edit');
    await tester.enterText(find.byKey(const Key('budget-amount')), '750.50');
    await tap(find.byKey(const Key('budget-create')));
    expect((await repository.budgets()).single.id, budget.id);
    expect((await repository.budgets()).single.amount, 750.50);
    await budgetAction('Delete');
    await tap(find.text('Cancel'));
    expect((await repository.budgets()).length, 1);

    transport.disconnected = true;
    await tap(find.byTooltip('Refresh budgets'));
    expect(
      find.textContaining('Unable to connect to Spendly.'),
      findsOneWidget,
    );
    expect(find.text('transport'), findsNothing);
    transport.disconnected = false;
    await tap(find.text('Retry'));
    expect(find.text('transport'), findsOneWidget);

    await budgetAction('Delete');
    await tap(find.text('Delete'));
    expect(await repository.budgets(), isEmpty);
    expect(find.text('No budget is configured.'), findsOneWidget);
    await tap(find.text('Add budget'));
    await tester.enterText(find.byKey(const Key('budget-amount')), '300');
    await tester.enterText(find.byKey(const Key('budget-category')), 'food');
    transport.disconnected = true;
    await tap(find.byKey(const Key('budget-create')));
    expect(
      find.textContaining('Your change may have been saved.'),
      findsOneWidget,
    );
    expect(
      transport.failedWrites,
      1,
      reason: 'Writes must not retry silently.',
    );
    expect(
      tester
          .widget<TextField>(find.byKey(const Key('budget-amount')))
          .controller!
          .text,
      '300',
    );
    transport.disconnected = false;
    // Check server state before explicitly resubmitting an uncertain write.
    expect(await repository.budgets(), isEmpty);
    await tap(find.byKey(const Key('budget-create')));
    expect((await repository.budgets()).single.amount, 300);
    debugPrint('SPENDLY_FINANCE:budget-crud-cancel-socket-recovery:passed');

    await repository.addTransaction(
      timestamp: today.add(const Duration(hours: 12)),
      amount: 125.50,
      category: 'food',
      transactionType: 'expense',
      merchant: 'Synthetic expense',
    );
    await repository.addTransaction(
      timestamp: today.add(const Duration(hours: 13)),
      amount: 1000,
      category: 'salary',
      transactionType: 'income',
      merchant: 'Synthetic income',
    );
    await show(const TransactionHistoryScreen());
    expect(find.text('Synthetic expense'), findsOneWidget);
    expect(find.text('Synthetic income'), findsOneWidget);
    await tap(find.byTooltip('Transaction actions').first);
    await tap(find.text('Delete'));
    await tap(find.text('Cancel'));
    expect((await repository.transactions()).length, 2);
    transport.disconnected = true;
    await tap(find.byTooltip('Refresh transactions'));
    expect(
      find.textContaining('Unable to connect to Spendly.'),
      findsOneWidget,
    );
    expect(find.text('Synthetic expense'), findsNothing);
    transport.disconnected = false;
    await tap(find.text('Retry'));
    expect(find.text('Synthetic expense'), findsOneWidget);
    await tap(find.byTooltip('Transaction actions').first);
    await tap(find.text('Delete'));
    await tap(find.text('Delete'));
    expect((await repository.transactions()).length, 1);
    debugPrint(
      'SPENDLY_FINANCE:transaction-delete-cancel-socket-recovery:passed',
    );

    await show(const AnalyticsScreen());
    for (final label in ['Daily', 'Weekly', 'Monthly', '3 months', 'Yearly']) {
      final chip = find.widgetWithText(ChoiceChip, label);
      await tap(chip);
      expect(tester.widget<ChoiceChip>(chip).selected, true);
    }
    expect(
      transport.analyticsResolutions,
      containsAll(['daily', 'weekly', 'monthly', 'quarterly', 'yearly']),
    );
    transport.disconnected = true;
    await tap(find.byTooltip('Refresh analytics'));
    expect(
      find.textContaining('Unable to connect to Spendly.'),
      findsOneWidget,
    );
    transport.disconnected = false;
    await tap(find.text('Retry'));
    expect(find.text('Cash-flow trend'), findsOneWidget);
    expect(
      tester
          .widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'Yearly'))
          .selected,
      true,
    );
    debugPrint('SPENDLY_FINANCE:analytics-filters-socket-recovery:passed');

    await show(const DashboardScreen());
    transport.disconnected = true;
    await tap(find.byTooltip('Refresh dashboard'));
    expect(find.textContaining('Unable to connect to Spendly.'), findsWidgets);
    transport.disconnected = false;
    await tap(find.byTooltip('Refresh dashboard'));
    expect(find.textContaining('Unable to connect to Spendly.'), findsNothing);
    debugPrint('SPENDLY_FINANCE:dashboard-socket-recovery:passed');
  });
}
