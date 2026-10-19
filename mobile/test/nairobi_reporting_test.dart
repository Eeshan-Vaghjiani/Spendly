import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/core/reporting_time.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/budget_screen.dart';
import 'package:spending_support/presentation/screens/transaction_entry_screen.dart';
import 'widget_test.dart' show FakeRepository;

void main() {
  test(
    'Nairobi wall time roundtrips once and preserves calendar-only dates',
    () {
      for (final text in [
        '2026-01-04T21:30:00Z',
        '2026-01-05T00:30:00+03:00',
      ]) {
        final instant = DateTime.parse(text);
        final wall = nairobiWallTime(instant);
        expect(
          wall.isUtc,
          true,
        ); // Wall-clock container is independent of device DST.
        expect(wall.day, 5);
        expect(wall.hour, 0);
        expect(nairobiInstant(wall), instant.toUtc());
        expect(nairobiDate(instant), DateTime.utc(2026, 1, 5));
      }
      expect(calendarDate(DateTime(2026, 1, 5)), DateTime.utc(2026, 1, 5));
      final dstBoundary = DateTime.parse('2026-03-07T23:30:00Z');
      final wall = nairobiWallTime(dstBoundary);
      expect(wall, DateTime.utc(2026, 3, 8, 2, 30));
      expect(nairobiInstant(wall), dstBoundary);
    },
  );
  testWidgets('budget includes Nairobi midnight and excludes next local day', (
    tester,
  ) async {
    final repository = FakeRepository();
    repository.createdBudgets.add(
      BudgetRecord(
        id: 'day',
        periodStart: DateTime(2026, 1, 5),
        periodEnd: DateTime(2026, 1, 5),
        category: 'total',
        amount: 100,
      ),
    );
    for (final entry in [
      ('2026-01-04T20:59:59Z', 10.0),
      ('2026-01-04T21:00:00Z', 20.0),
      ('2026-01-05T20:59:59Z', 30.0),
      ('2026-01-05T21:00:00Z', 40.0),
    ]) {
      repository.createdTransactions.add(
        TransactionRecord(
          id: entry.$1,
          timestamp: DateTime.parse(entry.$1),
          amount: entry.$2,
          category: 'food',
          transactionType: 'expense',
          isRecurring: false,
        ),
      );
    }
    await tester.pumpWidget(
      ProviderScope(
        overrides: [repositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: BudgetScreen()),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('KES 50.00 of KES 100.00'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets('editing an unchanged transaction preserves its UTC instant', (
    tester,
  ) async {
    final repository = FakeRepository();
    final transaction = TransactionRecord(
      id: 'edit',
      timestamp: DateTime.parse('2026-01-04T21:30:00Z'),
      amount: 100,
      category: 'food',
      transactionType: 'expense',
      isRecurring: false,
    );
    repository.createdTransactions.add(transaction);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [repositoryProvider.overrideWithValue(repository)],
        child: MaterialApp(
          home: TransactionEntryScreen(transaction: transaction),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('2026-01-05 00:30'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('transaction-save')));
    await tester.tap(find.byKey(const Key('transaction-save')));
    await tester.pumpAndSettle();
    expect(
      repository.createdTransactions.single.timestamp.toUtc(),
      transaction.timestamp,
    );
    expect(tester.takeException(), isNull);
  });
}
