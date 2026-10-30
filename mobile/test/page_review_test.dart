import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/core/theme/app_theme.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/alert_screen.dart';
import 'package:spending_support/presentation/screens/analysis_history_screen.dart';
import 'package:spending_support/presentation/screens/analytics_screen.dart';
import 'package:spending_support/presentation/screens/budget_screen.dart';
import 'package:spending_support/presentation/screens/consent_setup_screen.dart';
import 'package:spending_support/presentation/screens/dashboard_screen.dart';
import 'package:spending_support/presentation/screens/forecast_detail_screen.dart';
import 'package:spending_support/presentation/screens/home_shell.dart';
import 'package:spending_support/presentation/screens/login_screen.dart';
import 'package:spending_support/presentation/screens/more_screen.dart';
import 'package:spending_support/presentation/screens/onboarding_screen.dart';
import 'package:spending_support/presentation/screens/profile_screen.dart';
import 'package:spending_support/presentation/screens/recommendations_screen.dart';
import 'package:spending_support/presentation/screens/register_screen.dart';
import 'package:spending_support/presentation/screens/splash_screen.dart';
import 'package:spending_support/presentation/screens/transaction_entry_screen.dart';
import 'package:spending_support/presentation/screens/transaction_history_screen.dart';
import 'package:spending_support/presentation/screens/transaction_upload_screen.dart';

import 'widget_test.dart' show FakeGoogleIdentity, FakeRepository;

const _user = UserProfile(
  id: 'review-user',
  email: 'synthetic-page-review@example.invalid',
  displayName: 'Synthetic page review',
  username: 'synthetic_page_review',
);

class _ReviewRepository extends FakeRepository {
  _ReviewRepository() : super(restoredUser: _user) {
    createdTransactions.add(
      TransactionRecord(
        id: 'review-expense',
        timestamp: DateTime.utc(2026, 10, 19),
        amount: 1500000.25,
        category: 'household_maintenance',
        transactionType: 'expense',
        isRecurring: false,
        merchant: 'Synthetic household maintenance shop',
      ),
    );
  }

  bool offline = false;
  bool empty = false;
  Completer<CashflowAnalytics>? pendingAnalytics;

  @override
  Future<CashflowAnalytics> cashflowAnalytics(String resolution) {
    if (offline) {
      return Future.error(Exception('Synthetic connection unavailable'));
    }
    if (pendingAnalytics != null) return pendingAnalytics!.future;
    return super.cashflowAnalytics(resolution);
  }

  @override
  Future<List<Map<String, dynamic>>> history(String resource) async {
    if (offline) throw Exception('Synthetic connection unavailable');
    if (empty) return [];
    return switch (resource) {
      'forecasts' => [
        {
          'predicted_spending': 1500000.25,
          'period_start': '2026-10-19',
          'period_end': '2026-10-25',
          'actual_spending': 1250000.25,
          'data_readiness_percent': 100,
          'history_weeks': 8,
        },
      ],
      'alerts' => [
        {
          'is_unusual_spending': true,
          'explanation': 'Review this synthetic entry.',
        },
      ],
      _ => [
        {
          'title': 'Review your household maintenance budget',
          'suggested_action': 'Check the amount against your intended budget.',
        },
      ],
    };
  }
}

Future<void> _show(
  WidgetTester tester,
  Widget page,
  FakeRepository repository, {
  Size size = const Size(320, 640),
  double scale = 2,
  bool settle = true,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        repositoryProvider.overrideWithValue(repository),
        googleIdentityProvider.overrideWithValue(FakeGoogleIdentity()),
      ],
      child: MaterialApp(
        theme: AppTheme.light(),
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(
            context,
          ).copyWith(textScaler: TextScaler.linear(scale)),
          child: child!,
        ),
        home: page,
      ),
    ),
  );
  if (settle) await tester.pumpAndSettle();
  expect(tester.takeException(), isNull);
}

Future<void> _scrollPage(WidgetTester tester) async {
  final vertical = find.byWidgetPredicate(
    (widget) =>
        widget is Scrollable && widget.axisDirection == AxisDirection.down,
  );
  if (vertical.evaluate().isEmpty) return;
  for (var step = 0; step < 30; step++) {
    final state = tester.state<ScrollableState>(vertical.first);
    if (state.position.extentAfter <= 0) break;
    await tester.drag(vertical.first, const Offset(0, -420));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  }
}

void main() {
  final basicPages = <String, Widget>{
    'dashboard': const DashboardScreen(),
    'analytics': const AnalyticsScreen(),
    'budgets': const BudgetScreen(),
    'transactions': const TransactionHistoryScreen(),
    'transaction entry': const TransactionEntryScreen(),
    'CSV upload': const TransactionUploadScreen(),
    'history': const AnalysisHistoryScreen(),
    'profile': const ProfileScreen(),
    'more': const MoreScreen(),
    'consent': const ConsentSetupScreen(),
    'registration': const RegisterScreen(isRoot: true),
    'login': const LoginScreen(),
    'onboarding': const OnboardingScreen(replay: true),
  };
  for (final entry in basicPages.entries) {
    testWidgets('${entry.key} page fits narrow screen at 200% text', (
      tester,
    ) async {
      await _show(tester, entry.value, _ReviewRepository());
      await _scrollPage(tester);
    });
  }

  testWidgets('forecast and spending review fit long financial values', (
    tester,
  ) async {
    final repository = _ReviewRepository();
    await _show(
      tester,
      ForecastDetailScreen(
        forecast: ForecastResult(
          modelVersion: 'v6-reference',
          periodStart: DateTime.utc(2026, 10, 19),
          periodEnd: DateTime.utc(2026, 10, 25),
          predictedSpending: 1500000.25,
          baselinePrediction: 1250000.25,
          forecastMethod: 'v6_reference_lstm',
        ),
      ),
      repository,
    );
    await _scrollPage(tester);
    await _show(
      tester,
      AlertScreen(alerts: repository.analysis.alerts),
      repository,
    );
    await _scrollPage(tester);
  });

  testWidgets(
    'closing transaction page while date picker is open ignores its result',
    (tester) async {
      final showing = ValueNotifier(true);
      addTearDown(showing.dispose);
      await _show(
        tester,
        ValueListenableBuilder<bool>(
          valueListenable: showing,
          builder: (_, value, _) =>
              value ? const TransactionEntryScreen() : const SizedBox(),
        ),
        _ReviewRepository(),
        scale: 1,
      );
      await tester.ensureVisible(find.text('Transaction date'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Transaction date'));
      await tester.pumpAndSettle();
      showing.value = false;
      await tester.pump();
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    },
  );

  for (final label in ['Starts', 'Ends']) {
    testWidgets(
      'closing budget editor while $label picker is open ignores its result',
      (tester) async {
        await _show(
          tester,
          const BudgetScreen(),
          _ReviewRepository(),
          scale: 1,
        );
        await tester.tap(find.text('Add budget'));
        await tester.pumpAndSettle();
        final editorContext = tester.element(
          find.byKey(const Key('budget-amount')),
        );
        final editorRoute = ModalRoute.of(editorContext)!;
        final navigator = Navigator.of(editorContext);
        await tester.tap(find.text(label));
        await tester.pumpAndSettle();
        navigator.removeRoute(editorRoute);
        await tester.pump();
        await tester.tap(find.text('OK'));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('long recommendation details can be read to the end', (
    tester,
  ) async {
    final advice = RecommendationResult(
      code: 'SYNTHETIC_REVIEW',
      title: 'Review your household maintenance budget',
      message: List.filled(
        15,
        'Review the recorded amount and intended budget.',
      ).join(' '),
      severity: 'high',
      reason: List.filled(8, 'Based on recorded synthetic spending.').join(' '),
      suggestedAction: 'Check the amount against your intended budget.',
      disclaimer: 'Synthetic recommendation details end here.',
    );
    await _show(
      tester,
      RecommendationsScreen(recommendations: [advice]),
      _ReviewRepository(),
    );
    await tester.ensureVisible(find.text('Why am I seeing this?'));
    await tester.pumpAndSettle();
    expect(find.text('Why am I seeing this?').hitTestable(), findsOneWidget);
    await tester.tap(find.text('Why am I seeing this?'));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    await tester.ensureVisible(find.text(advice.disclaimer));
    await tester.pumpAndSettle();
    expect(find.text(advice.disclaimer).hitTestable(), findsOneWidget);
  });

  testWidgets(
    'history offline errors are handled for all tabs and retry recovers',
    (tester) async {
      final repository = _ReviewRepository()..offline = true;
      await _show(tester, const AnalysisHistoryScreen(), repository);
      expect(find.text('Retry'), findsOneWidget);
      repository.offline = false;
      await tester.ensureVisible(find.text('Retry'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();
      expect(find.textContaining('1,500,000'), findsOneWidget);
      for (final tab in ['Alerts', 'Advice']) {
        await tester.tap(find.text(tab));
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
        expect(find.text('Retry'), findsNothing);
      }
    },
  );

  testWidgets(
    'analytics loading can be left safely and offline retry recovers',
    (tester) async {
      final repository = _ReviewRepository()
        ..pendingAnalytics = Completer<CashflowAnalytics>();
      await _show(tester, const AnalyticsScreen(), repository, settle: false);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
      repository.pendingAnalytics!.complete(
        await FakeRepository().cashflowAnalytics('monthly'),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      repository.pendingAnalytics = null;
      repository.offline = true;
      await _show(tester, const AnalyticsScreen(), repository);
      repository.offline = false;
      await tester.ensureVisible(find.text('Retry'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Retry'));
      await tester.pumpAndSettle();
      expect(find.text('Income, expenses and savings'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('home navigation and splash fit short landscape at 200% text', (
    tester,
  ) async {
    await _show(
      tester,
      const HomeShell(),
      _ReviewRepository(),
      size: const Size(640, 320),
    );
    for (final icon in [
      Icons.receipt_long_outlined,
      Icons.savings_outlined,
      Icons.show_chart_outlined,
      Icons.more_horiz,
    ]) {
      await tester.tap(find.byIcon(icon).last);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    }
    await _show(
      tester,
      const SplashScreen(),
      _ReviewRepository(),
      size: const Size(640, 320),
      settle: false,
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
