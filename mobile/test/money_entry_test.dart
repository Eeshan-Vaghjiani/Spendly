import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/budget_screen.dart';
import 'package:spending_support/presentation/screens/transaction_entry_screen.dart';

import 'widget_test.dart' show FakeRepository;

class PendingRepository extends FakeRepository {
  int transactionWrites = 0;
  int budgetWrites = 0;
  final pendingTransaction = Completer<TransactionRecord>();
  final budget = Completer<BudgetRecord>();

  @override
  Future<TransactionRecord> addTransaction({
    required DateTime timestamp,
    required double amount,
    required String category,
    required String transactionType,
    String? merchant,
    bool isRecurring = false,
  }) {
    transactionWrites++;
    return pendingTransaction.future;
  }

  @override
  Future<BudgetRecord> createBudget({
    required DateTime periodStart,
    required DateTime periodEnd,
    required String category,
    required double amount,
  }) {
    budgetWrites++;
    return budget.future;
  }
}

Future<void> showForm(
  WidgetTester tester,
  FakeRepository repository, {
  required bool budget,
}) async {
  tester.view.physicalSize = const Size(1000, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [repositoryProvider.overrideWithValue(repository)],
      child: MaterialApp(
        home: budget ? const BudgetScreen() : const TransactionEntryScreen(),
      ),
    ),
  );
  await tester.pumpAndSettle();
  if (budget) {
    await tester.tap(find.text('Add budget'));
    await tester.pumpAndSettle();
  } else {
    await tester.enterText(
      find.byKey(const Key('transaction-category')),
      'food',
    );
  }
}

void main() {
  for (final budget in [false, true]) {
    final prefix = budget ? 'budget' : 'transaction';
    final saveKey = budget ? 'budget-create' : 'transaction-save';
    testWidgets(
      '$prefix rejects nonfinite and nonpositive amounts before a write',
      (tester) async {
        final repository = FakeRepository();
        await showForm(tester, repository, budget: budget);
        for (final text in ['NaN', 'Infinity', '1e309', '0', '-1']) {
          await tester.enterText(find.byKey(Key('$prefix-amount')), text);
          await tester.tap(find.byKey(Key(saveKey)));
          await tester.pumpAndSettle();
          expect(repository.createdTransactions, isEmpty, reason: text);
          expect(repository.createdBudgets, isEmpty, reason: text);
          expect(find.textContaining('greater than zero'), findsOneWidget);
        }
      },
    );

    testWidgets('$prefix accepts a positive decimal amount', (tester) async {
      final repository = FakeRepository();
      await showForm(tester, repository, budget: budget);
      await tester.enterText(find.byKey(Key('$prefix-amount')), '123.45');
      await tester.tap(find.byKey(Key(saveKey)));
      await tester.pumpAndSettle();
      final value = budget
          ? repository.createdBudgets.single.amount
          : repository.createdTransactions.single.amount;
      expect(value, 123.45);
      expect(tester.takeException(), isNull);
    });

    testWidgets('$prefix ignores repeated saves before button rebuild', (
      tester,
    ) async {
      final repository = PendingRepository();
      await showForm(tester, repository, budget: budget);
      await tester.enterText(find.byKey(Key('$prefix-amount')), '123.45');
      final callback = tester
          .widget<FilledButton>(find.byKey(Key(saveKey)))
          .onPressed!;
      callback();
      callback();
      await tester.pump();
      expect(
        budget ? repository.budgetWrites : repository.transactionWrites,
        1,
      );
      // Complete only after disposal to also verify existing async completion guards.
      await tester.pumpWidget(const SizedBox());
      if (budget) {
        repository.budget.complete(
          BudgetRecord(
            id: 'fixture',
            periodStart: DateTime(2026),
            periodEnd: DateTime(2026, 1, 7),
            category: 'total',
            amount: 123.45,
          ),
        );
      } else {
        repository.pendingTransaction.complete(
          TransactionRecord(
            id: 'fixture',
            timestamp: DateTime(2026),
            amount: 123.45,
            category: 'food',
            transactionType: 'expense',
            isRecurring: false,
          ),
        );
      }
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  }
}
