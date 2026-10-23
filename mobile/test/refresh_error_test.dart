import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/core/theme/app_theme.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/analytics_screen.dart';
import 'package:spending_support/presentation/screens/budget_screen.dart';
import 'package:spending_support/presentation/screens/dashboard_screen.dart';
import 'package:spending_support/presentation/screens/transaction_history_screen.dart';

import 'widget_test.dart' show FakeRepository;

class _FastFailureRepository extends FakeRepository {
  bool fail = false;
  Future<T> result<T>(Future<T> Function() online) => fail
      ? Future<T>.error(StateError('Synthetic connection refused'))
      : online();

  @override
  Future<List<BudgetRecord>> budgets() => result(super.budgets);
  @override
  Future<List<TransactionRecord>> transactions() => result(super.transactions);
  @override
  Future<CashflowAnalytics> cashflowAnalytics(String resolution) =>
      result(() => super.cashflowAnalytics(resolution));
  @override
  Future<DashboardSummary> dashboardSummary(String period) =>
      result(() => super.dashboardSummary(period));
}

void main() {
  for (final (screen, refresh) in <(Widget, String)>[
    (const BudgetScreen(), 'Refresh budgets'),
    (const TransactionHistoryScreen(), 'Refresh transactions'),
    (const AnalyticsScreen(), 'Refresh analytics'),
    (const DashboardScreen(), 'Refresh dashboard'),
  ]) {
    testWidgets('$refresh handles failures before the next frame and retries', (
      tester,
    ) async {
      final repository = _FastFailureRepository();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [repositoryProvider.overrideWithValue(repository)],
          child: MaterialApp(theme: AppTheme.light(), home: screen),
        ),
      );
      await tester.pumpAndSettle();
      repository.fail = true;
      await tester.tap(find.byTooltip(refresh));
      // A native connection refusal can complete before FutureBuilder has had
      // a frame to subscribe to the newly assigned future.
      await tester.idle();
      await tester.pumpAndSettle();
      expect(
        find.textContaining('Synthetic connection refused'),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
      repository.fail = false;
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();
      expect(find.textContaining('Synthetic connection refused'), findsNothing);
      expect(find.text('Retry'), findsNothing);
      expect(tester.takeException(), isNull);
    });
  }
}
