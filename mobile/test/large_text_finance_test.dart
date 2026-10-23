import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/core/theme/app_theme.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/budget_screen.dart';
import 'package:spending_support/presentation/screens/transaction_history_screen.dart';

import 'widget_test.dart' show FakeRepository;

Future<void> showFinanceScreen(
  WidgetTester tester,
  Widget screen,
  FakeRepository repository,
  double textScale,
) async {
  tester.view.physicalSize = const Size(320, 640);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [repositoryProvider.overrideWithValue(repository)],
      child: MaterialApp(
        theme: AppTheme.light(),
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(
            context,
          ).copyWith(textScaler: TextScaler.linear(textScale)),
          child: child!,
        ),
        home: screen,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  for (final textScale in [1.0, 2.0]) {
    testWidgets('budget amounts and actions fit at text scale $textScale', (
      tester,
    ) async {
      final repository = FakeRepository();
      repository.createdBudgets.add(
        BudgetRecord(
          id: 'synthetic-budget',
          category: 'total',
          amount: 1250000,
          periodStart: DateTime(2026, 10, 1),
          periodEnd: DateTime(2026, 10, 31),
        ),
      );
      repository.createdTransactions.add(
        TransactionRecord(
          id: 'synthetic-expense',
          timestamp: DateTime(2026, 10, 10),
          amount: 1500000,
          category: 'food',
          transactionType: 'expense',
          isRecurring: false,
        ),
      );
      await showFinanceScreen(
        tester,
        const BudgetScreen(),
        repository,
        textScale,
      );
      expect(tester.takeException(), isNull);
      expect(find.text('120% used'), findsOneWidget);
      expect(find.text('Spent KES 1,500,000.00'), findsOneWidget);
      expect(find.text('Limit KES 1,250,000.00'), findsOneWidget);
      expect(find.text('KES 250,000.00 over budget'), findsOneWidget);
      await tester.tap(find.byTooltip('Budget actions'));
      await tester.pumpAndSettle();
      expect(find.text('Edit'), findsOneWidget);
      expect(find.text('Delete'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.tap(find.text('Edit'));
      await tester.pumpAndSettle();
      expect(find.text('Edit weekly budget'), findsOneWidget);
      expect(find.text('1250000.00'), findsOneWidget);
      await tester.ensureVisible(find.byKey(const Key('budget-create')));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const Key('budget-create')).hitTestable(),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    });

    testWidgets('transaction amount stays readable at text scale $textScale', (
      tester,
    ) async {
      final repository = FakeRepository();
      repository.createdTransactions.add(
        TransactionRecord(
          id: 'synthetic-expense',
          timestamp: DateTime(2026, 10, 10),
          amount: 1500000,
          category: 'household_maintenance',
          transactionType: 'expense',
          isRecurring: false,
          merchant: 'Synthetic household maintenance shop',
        ),
      );
      await showFinanceScreen(
        tester,
        const TransactionHistoryScreen(),
        repository,
        textScale,
      );
      expect(tester.takeException(), isNull);
      expect(find.textContaining('1,500,000.00'), findsOneWidget);
      await tester.tap(find.textContaining('1,500,000.00'));
      await tester.pumpAndSettle();
      expect(find.text('Edit transaction'), findsOneWidget);
      expect(find.text('1500000.00'), findsOneWidget);
      await tester.ensureVisible(find.byKey(const Key('transaction-save')));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const Key('transaction-save')).hitTestable(),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    });
  }
}
