import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/core/theme/app_theme.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/transaction_history_screen.dart';
import 'package:spending_support/presentation/screens/home_shell.dart';
import 'package:spending_support/presentation/screens/analytics_screen.dart';
import 'package:spending_support/presentation/screens/budget_screen.dart';
import 'package:spending_support/presentation/widgets/expense_category_chart.dart';
import 'package:spending_support/presentation/widgets/forecast_comparison.dart';
import 'package:spending_support/presentation/widgets/transaction_source_icon.dart';
import 'widget_test.dart' show FakeRepository;

class _HistoryRepository extends FakeRepository {
  bool offline = true;
  @override
  Future<List<Map<String, dynamic>>> history(String resource) async {
    if (offline) throw Exception('synthetic offline');
    return [];
  }
}

void main() {
  testWidgets('dashboard links open analytics and budgets', (tester) async {
    tester.view.physicalSize = const Size(800, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [repositoryProvider.overrideWithValue(FakeRepository())],
        child: MaterialApp(theme: AppTheme.light(), home: const HomeShell()),
      ),
    );
    await tester.pumpAndSettle();
    await tester.ensureVisible(
      find.byKey(const Key('dashboard-view-analytics')),
    );
    await tester.tap(find.byKey(const Key('dashboard-view-analytics')));
    await tester.pumpAndSettle();
    expect(find.byType(AnalyticsScreen), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.byKey(const Key('dashboard-view-budgets')));
    await tester.tap(find.byKey(const Key('dashboard-view-budgets')));
    await tester.pumpAndSettle();
    expect(find.byType(BudgetScreen), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
  testWidgets('forecast history retry survives a replaced dashboard', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(800, 1800);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final repo = _HistoryRepository();
    final container = ProviderContainer(
      overrides: [repositoryProvider.overrideWithValue(repo)],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(theme: AppTheme.light(), home: const HomeShell()),
      ),
    );
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.byKey(const Key('open-weekly-forecast')),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('open-weekly-forecast')));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Retry history'),
      300,
      scrollable: find.byType(Scrollable).last,
    );
    container.read(financialDataRevisionProvider.notifier).state++;
    await tester.pumpAndSettle();
    repo.offline = false;
    await tester.tap(find.text('Retry history'));
    await tester.pumpAndSettle();
    expect(
      find.textContaining('No completed recorded comparisons yet.'),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });
  for (final (source, label) in [
    ('mpesa_sms', 'Imported from M-PESA SMS'),
    ('manual', 'Added manually'),
    ('csv_upload', 'Imported from CSV'),
    ('admin', 'Added by support'),
    ('future-source', 'Source unavailable'),
  ]) {
    testWidgets('source $source is labelled and explains itself on tap', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: TransactionSourceIcon(source: source)),
        ),
      );
      expect(find.byTooltip(label), findsOneWidget);
      await tester.tap(find.byTooltip(label));
      await tester.pumpAndSettle();
      expect(find.widgetWithText(AlertDialog, label), findsOneWidget);
      await tester.tap(find.text('Close'));
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsNothing);
    });
  }

  test('missing provenance is not silently labelled manual', () {
    final row = TransactionRecord.fromJson({
      'id': 'old',
      'transaction_timestamp': '2026-10-20T12:00:00Z',
      'amount': 10,
      'category': 'food',
      'transaction_type': 'expense',
    });
    expect(row.source, 'unknown');
  });

  test(
    'older cashflow response is unavailable rather than zero categories',
    () {
      final json = <String, dynamic>{
        'resolution': 'monthly',
        'period_start': '2026-10-01',
        'period_end': '2026-10-31',
        'summary': {
          'income': 100,
          'expense': 31,
          'net': 69,
          'cash_balance': 69,
          'savings_rate': 69,
          'budgeted': 50,
        },
        'series': <dynamic>[],
      };
      expect(
        CashflowAnalytics.fromJson(json).expenseCategoriesAvailable,
        isFalse,
      );
      final current = CashflowAnalytics.fromJson({
        ...json,
        'expense_categories': [
          {'category': 'food', 'amount': 31.25},
        ],
      });
      expect(current.expenseCategoriesAvailable, isTrue);
      expect(current.expenseCategories.single.amount, 31.25);
    },
  );

  testWidgets('unavailable category evidence is not presented as no expenses', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ExpenseCategoryChart(
            range: 'Selected range',
            items: [],
            available: false,
          ),
        ),
      ),
    );
    expect(
      find.textContaining('Category breakdown is unavailable.'),
      findsOneWidget,
    );
    expect(find.text('No recorded expenses in this period.'), findsNothing);
  });

  testWidgets(
    'transaction source and reversed status survive narrow large text',
    (tester) async {
      tester.view.physicalSize = const Size(320, 640);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final repo = FakeRepository();
      repo.createdTransactions.add(
        TransactionRecord(
          id: 'sms-row',
          timestamp: DateTime.utc(2026, 10, 20),
          amount: 100,
          category: 'airtime',
          transactionType: 'expense',
          isRecurring: false,
          source: 'mpesa_sms',
          isReversed: true,
        ),
      );
      await tester.pumpWidget(
        ProviderScope(
          overrides: [repositoryProvider.overrideWithValue(repo)],
          child: MaterialApp(
            theme: AppTheme.light(),
            builder: (context, child) => MediaQuery(
              data: MediaQuery.of(
                context,
              ).copyWith(textScaler: const TextScaler.linear(2)),
              child: child!,
            ),
            home: const TransactionHistoryScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Reversed — excluded from totals'), findsOneWidget);
      expect(find.text('M-PESA SMS'), findsNothing);
      expect(find.byTooltip('Imported from M-PESA SMS'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('category chart retains the tail total and handles no expenses', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ExpenseCategoryChart(
            range: 'Selected range',
            items: List.generate(
              6,
              (i) => ExpenseCategory(
                category: 'category_$i',
                amount: (6 - i).toDouble(),
              ),
            ),
          ),
        ),
      ),
    );
    expect(find.text('Other categories'), findsOneWidget);
    expect(
      find.descendant(
        of: find.byKey(const ValueKey('expense-category-Other categories')),
        matching: find.text('KES 3.00'),
      ),
      findsOneWidget,
    );
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ExpenseCategoryChart(range: 'Selected range', items: []),
        ),
      ),
    );
    expect(find.text('No recorded expenses in this period.'), findsOneWidget);
  });

  testWidgets(
    'history omits pending weeks, deduplicates and retries a failed load',
    (tester) async {
      var fails = true;
      Future<List<Map<String, dynamic>>> load() async {
        if (fails) throw Exception('synthetic offline');
        return [
          {
            'period_start': '2020-01-06',
            'period_end': '2020-01-12',
            'predicted_spending': 120,
            'actual_spending': 0,
          },
          {
            'period_start': '2020-01-06',
            'period_end': '2020-01-12',
            'predicted_spending': 150,
            'actual_spending': 10,
          },
          {
            'period_start': '2099-01-01',
            'period_end': '2099-01-07',
            'predicted_spending': 500,
            'actual_spending': null,
          },
        ];
      }

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: ForecastHistoryPanel(load: load),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(
        find.text('Could not load saved forecast comparisons.'),
        findsOneWidget,
      );
      fails = false;
      await tester.tap(find.text('Retry history'));
      await tester.pumpAndSettle();
      expect(find.byType(ForecastComparison), findsOneWidget);
      expect(find.text('KES 120.00'), findsOneWidget);
      expect(find.text('KES 0.00'), findsOneWidget);
      expect(find.textContaining('2099-01-01'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );
}
