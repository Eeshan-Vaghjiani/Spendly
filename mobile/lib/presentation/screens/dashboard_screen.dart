import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_theme.dart';
import '../../data/models/models.dart';
import '../controllers/providers.dart';
import '../widgets/common.dart';
import 'alert_screen.dart';
import 'forecast_detail_screen.dart';
import 'recommendations_screen.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  late Future<_DashboardSnapshot> _snapshot;

  @override
  void initState() {
    super.initState();
    _loadSnapshot();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(analysisControllerProvider.notifier).loadLatest();
    });
  }

  void _loadSnapshot() {
    final repository = ref.read(repositoryProvider);
    _snapshot = Future.wait([repository.transactions(), repository.budgets()])
        .then((values) {
          return _DashboardSnapshot(
            values[0] as List<TransactionRecord>,
            values[1] as List<BudgetRecord>,
          );
        });
  }

  Future<void> _refresh() async {
    setState(_loadSnapshot);
    await ref.read(analysisControllerProvider.notifier).loadLatest();
  }

  @override
  Widget build(BuildContext context) {
    final analysis = ref.watch(analysisControllerProvider);
    final user = ref.watch(authControllerProvider).user;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            tooltip: 'Refresh dashboard',
            onPressed: _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Hello, ${user?.displayName.split(' ').first ?? 'there'}',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 4),
            Text(
              'Here is your spending picture at a glance.',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppColors.mutedInk),
            ),
            const SizedBox(height: 20),
            FutureBuilder<_DashboardSnapshot>(
              future: _snapshot,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const SizedBox(
                    height: 150,
                    child: Center(child: CircularProgressIndicator()),
                  );
                }
                if (snapshot.hasError) {
                  return ErrorPanel(
                    message: snapshot.error.toString(),
                    onRetry: () => setState(_loadSnapshot),
                  );
                }
                return _SpendingSummary(snapshot: snapshot.requireData);
              },
            ),
            const SizedBox(height: 20),
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Your latest insight',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
                FilledButton.icon(
                  key: const Key('run-analysis'),
                  onPressed: analysis.loading
                      ? null
                      : ref.read(analysisControllerProvider.notifier).run,
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('Refresh insights'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (analysis.loading)
              const Center(child: CircularProgressIndicator())
            else if (analysis.result != null)
              _AnalysisSummary(result: analysis.result!)
            else
              SoftPanel(
                child: Column(
                  children: [
                    Container(
                      width: 64,
                      height: 64,
                      decoration: BoxDecoration(
                        color: AppColors.mint.withValues(alpha: 0.5),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.insights_outlined,
                        size: 32,
                        color: AppColors.primary,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Build your first spending snapshot',
                      style: Theme.of(context).textTheme.titleMedium,
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      analysis.error ??
                          'Add transactions regularly, then refresh your insights.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Your first learning forecast is available after one recorded week. '
                      'It becomes more dependable as you approach eight weeks.',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.mutedInk,
                      ),
                    ),
                  ],
                ),
              ),
            const SizedBox(height: 16),
            const SoftPanel(
              padding: EdgeInsets.all(14),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.info_outline, size: 19, color: AppColors.mutedInk),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Insights help you plan and review entries. They are not '
                      'guarantees or fraud findings.',
                      style: TextStyle(color: AppColors.mutedInk, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DashboardSnapshot {
  const _DashboardSnapshot(this.transactions, this.budgets);

  final List<TransactionRecord> transactions;
  final List<BudgetRecord> budgets;
}

class _SpendingSummary extends StatelessWidget {
  const _SpendingSummary({required this.snapshot});

  final _DashboardSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final weekStart = now.subtract(Duration(days: now.weekday - 1));
    final spending = snapshot.transactions
        .where(
          (item) =>
              item.transactionType == 'expense' &&
              item.timestamp.isAfter(
                DateTime(weekStart.year, weekStart.month, weekStart.day),
              ),
        )
        .fold<double>(0, (sum, item) => sum + item.amount);
    final income = snapshot.transactions
        .where(
          (item) =>
              item.transactionType == 'income' &&
              item.timestamp.isAfter(
                DateTime(weekStart.year, weekStart.month, weekStart.day),
              ),
        )
        .fold<double>(0, (sum, item) => sum + item.amount);
    final totalIncome = snapshot.transactions
        .where((item) => item.transactionType == 'income')
        .fold<double>(0, (sum, item) => sum + item.amount);
    final totalExpenses = snapshot.transactions
        .where((item) => item.transactionType == 'expense')
        .fold<double>(0, (sum, item) => sum + item.amount);
    final cashBalance = totalIncome - totalExpenses;
    final activeBudgets = snapshot.budgets
        .where(
          (budget) =>
              !now.isBefore(budget.periodStart) &&
              !now.isAfter(budget.periodEnd.add(const Duration(days: 1))),
        )
        .toList(growable: false);
    final totalBudgets = activeBudgets
        .where((item) => item.category.toLowerCase() == 'total')
        .toList(growable: false);
    final budgetsForSummary = totalBudgets.isNotEmpty
        ? totalBudgets
        : activeBudgets;
    final budget = budgetsForSummary.fold<double>(
      0,
      (sum, item) => sum + item.amount,
    );
    var budgetSpending = 0.0;
    for (final transaction in snapshot.transactions.where(
      (item) => item.transactionType == 'expense',
    )) {
      final transactionDate = transaction.timestamp.toLocal();
      final matches = budgetsForSummary.any((item) {
        final start = DateTime(
          item.periodStart.year,
          item.periodStart.month,
          item.periodStart.day,
        );
        final end = DateTime(
          item.periodEnd.year,
          item.periodEnd.month,
          item.periodEnd.day,
          23,
          59,
          59,
        );
        return !transactionDate.isBefore(start) &&
            !transactionDate.isAfter(end) &&
            (item.category.toLowerCase() == 'total' ||
                item.category.toLowerCase() ==
                    transaction.category.toLowerCase());
      });
      if (matches) budgetSpending += transaction.amount;
    }
    final budgetPercent = budget > 0 ? budgetSpending / budget * 100 : 0.0;
    final overBudget = budget > 0 && budgetPercent > 100;
    final categories = <String, double>{};
    for (final transaction in snapshot.transactions.where(
      (item) => item.transactionType == 'expense',
    )) {
      categories.update(
        transaction.category,
        (value) => value + transaction.amount,
        ifAbsent: () => transaction.amount,
      );
    }
    final topCategory = categories.entries.isEmpty
        ? 'No data'
        : (categories.entries.toList()
                ..sort((left, right) => right.value.compareTo(left.value)))
              .first
              .key;
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth > 720
            ? (constraints.maxWidth - 24) / 3
            : (constraints.maxWidth - 12) / 2;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            SizedBox(
              width: width,
              height: 170,
              child: SummaryCard(
                title: 'Spent this week',
                value: NumberFormat.currency(
                  symbol: 'KES ',
                  decimalDigits: 0,
                ).format(spending),
                icon: Icons.arrow_downward_rounded,
                accentColor: AppColors.expense,
              ),
            ),
            SizedBox(
              width: width,
              height: 170,
              child: SummaryCard(
                title: 'Income this week',
                value: NumberFormat.currency(
                  symbol: 'KES ',
                  decimalDigits: 0,
                ).format(income),
                icon: Icons.arrow_upward_rounded,
                accentColor: AppColors.income,
              ),
            ),
            SizedBox(
              width: width,
              height: 170,
              child: SummaryCard(
                title: overBudget ? 'Budget exceeded' : 'Active budget',
                value: budget > 0
                    ? '${budgetPercent.toStringAsFixed(0)}% used'
                    : 'Not set',
                icon: overBudget
                    ? Icons.warning_amber_rounded
                    : Icons.savings_outlined,
                subtitle: budget > 0
                    ? overBudget
                          ? '${NumberFormat.currency(symbol: 'KES ', decimalDigits: 0).format(budgetSpending - budget)} over'
                          : '${NumberFormat.currency(symbol: 'KES ', decimalDigits: 0).format(budget - budgetSpending)} left'
                    : 'Create one in Budgets',
                accentColor: overBudget ? AppColors.expense : AppColors.primary,
              ),
            ),
            SizedBox(
              width: width,
              height: 170,
              child: SummaryCard(
                title: cashBalance < 0 ? 'Cash shortfall' : 'Available balance',
                value: NumberFormat.currency(
                  symbol: 'KES ',
                  decimalDigits: 0,
                ).format(cashBalance.abs()),
                icon: Icons.account_balance_wallet_outlined,
                subtitle: 'All entered income minus expenses',
                accentColor: cashBalance < 0
                    ? AppColors.expense
                    : AppColors.primary,
              ),
            ),
            SizedBox(
              width: width,
              height: 170,
              child: SummaryCard(
                title: income - spending < 0
                    ? 'Weekly shortfall'
                    : 'Saved this week',
                value: NumberFormat.currency(
                  symbol: 'KES ',
                  decimalDigits: 0,
                ).format((income - spending).abs()),
                icon: income - spending < 0
                    ? Icons.trending_down
                    : Icons.savings_outlined,
                accentColor: income - spending < 0
                    ? AppColors.expense
                    : AppColors.income,
              ),
            ),
            SizedBox(
              width: width,
              height: 170,
              child: SummaryCard(
                title: 'Top spending area',
                value: topCategory.replaceAll('_', ' '),
                icon: Icons.category_outlined,
              ),
            ),
          ],
        );
      },
    );
  }
}

class _AnalysisSummary extends StatelessWidget {
  const _AnalysisSummary({required this.result});

  final AnalysisResult result;

  @override
  Widget build(BuildContext context) {
    final unusualCount = result.alerts
        .where((alert) => alert.isUnusualSpending)
        .length;
    final unusual = unusualCount > 0;
    final firstRecommendation = result.recommendations.firstOrNull;
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth > 720
            ? (constraints.maxWidth - 24) / 3
            : constraints.maxWidth;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            SizedBox(
              width: width,
              height: 170,
              child: SummaryCard(
                title: 'Next 7 days',
                value: NumberFormat.currency(
                  symbol: 'KES ',
                  decimalDigits: 0,
                ).format(result.forecast.predictedSpending),
                icon: Icons.trending_up,
                subtitle:
                    '${result.forecast.dataReadinessPercent}% data readiness · '
                    'week ${result.forecast.historyWeeks}/8',
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) =>
                        ForecastDetailScreen(forecast: result.forecast),
                  ),
                ),
              ),
            ),
            SizedBox(
              width: width,
              height: 170,
              child: SummaryCard(
                title: 'Spending check',
                value: unusual
                    ? '$unusualCount ${unusualCount == 1 ? 'item' : 'items'} to review'
                    : 'All looks usual',
                icon: unusual
                    ? Icons.warning_amber
                    : Icons.check_circle_outline,
                subtitle: unusual
                    ? 'A quick check is enough'
                    : 'Nothing needs attention',
                accentColor: unusual
                    ? const Color(0xFF9A6200)
                    : AppColors.primary,
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => AlertScreen(alerts: result.alerts),
                  ),
                ),
              ),
            ),
            SizedBox(
              width: width,
              height: 170,
              child: SummaryCard(
                title: 'Your next step',
                value: firstRecommendation?.title ?? 'No action needed',
                icon: Icons.lightbulb_outline,
                subtitle: firstRecommendation == null
                    ? 'You are up to date'
                    : 'Tap for one simple action',
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (_) => RecommendationsScreen(
                      recommendations: result.recommendations,
                    ),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}
