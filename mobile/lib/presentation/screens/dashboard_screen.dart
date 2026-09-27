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
  const DashboardScreen({super.key, this.onOpenMenu});

  final VoidCallback? onOpenMenu;

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  late Future<DashboardSummary> _snapshot;

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
    _snapshot = repository.dashboardSummary(ref.read(dashboardPeriodProvider));
  }

  void _selectPeriod(String period) {
    if (period == ref.read(dashboardPeriodProvider)) return;
    ref.read(dashboardPeriodProvider.notifier).state = period;
    setState(_loadSnapshot);
  }

  Future<void> _refresh() async {
    setState(_loadSnapshot);
    await ref.read(analysisControllerProvider.notifier).loadLatest();
  }

  @override
  Widget build(BuildContext context) {
    final analysis = ref.watch(analysisControllerProvider);
    final user = ref.watch(authControllerProvider).user;
    final selectedPeriod = ref.watch(dashboardPeriodProvider);
    return Scaffold(
      appBar: AppBar(
        leading: widget.onOpenMenu == null
            ? null
            : IconButton(
                key: const Key('open-quick-access'),
                tooltip: 'Open quick access menu',
                onPressed: widget.onOpenMenu,
                icon: const Icon(Icons.menu),
              ),
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
              'Hello, ${user?.username.isNotEmpty == true ? user!.username : 'there'}',
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
            Text(
              'Dashboard period',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 8),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children:
                    const {
                          'weekly': 'Weekly',
                          'monthly': 'Monthly',
                          'last_3_months': 'Last 3 Months',
                          'yearly': 'Yearly',
                          'all_time': 'All Time',
                        }.entries
                        .map((entry) {
                          return Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: ChoiceChip(
                              key: Key('dashboard-period-${entry.key}'),
                              label: Text(entry.value),
                              selected: selectedPeriod == entry.key,
                              onSelected: (_) => _selectPeriod(entry.key),
                            ),
                          );
                        })
                        .toList(growable: false),
              ),
            ),
            const SizedBox(height: 14),
            FutureBuilder<DashboardSummary>(
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
                return _SpendingSummary(summary: snapshot.requireData);
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
            if (analysis.error?.contains('Confirm') == true ||
                analysis.error?.contains('complete recorded weeks') == true)
              OutlinedButton.icon(
                icon: const Icon(Icons.fact_check_outlined),
                label: const Text('Confirm recorded history'),
                onPressed: () async {
                  final selected = await showDatePicker(
                    context: context,
                    initialDate: DateTime.now().subtract(
                      const Duration(days: 56),
                    ),
                    firstDate: DateTime(2020),
                    lastDate: DateTime.now(),
                    helpText: 'From when have you recorded all spending?',
                  );
                  if (!context.mounted || selected == null) return;
                  final confirmed = await showDialog<bool>(
                    context: context,
                    builder: (dialog) => AlertDialog(
                      title: const Text('Is your history complete?'),
                      content: const Text(
                        'Confirm only if all spending since this date is recorded, including weeks with no spending. Missing entries can make the estimate misleading. This estimates the current Monday–Sunday week using only earlier history.',
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(dialog, false),
                          child: const Text('Cancel'),
                        ),
                        FilledButton(
                          onPressed: () => Navigator.pop(dialog, true),
                          child: const Text('Confirm'),
                        ),
                      ],
                    ),
                  );
                  if (!context.mounted || confirmed != true) return;
                  final controller = ref.read(
                    analysisControllerProvider.notifier,
                  );
                  controller.historyCompleteFrom = selected;
                  await controller.run();
                },
              ),
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

class _SpendingSummary extends StatelessWidget {
  const _SpendingSummary({required this.summary});

  final DashboardSummary summary;

  String get _periodLabel => switch (summary.period) {
    'weekly' => 'this week',
    'monthly' => 'this month',
    'last_3_months' => 'in the last 3 months',
    'yearly' => 'this year',
    _ => 'across all time',
  };

  String _money(double value) =>
      NumberFormat.currency(symbol: 'KES ', decimalDigits: 0).format(value);

  @override
  Widget build(BuildContext context) {
    final start = summary.periodStart;
    final range = start == null
        ? 'No recorded transaction dates yet'
        : '${DateFormat.yMMMd().format(start)} – ${DateFormat.yMMMd().format(summary.periodEnd)}';
    final overBudget =
        summary.hasActiveBudget && summary.activeBudgetPercent > 100;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          range,
          key: const Key('dashboard-period-range'),
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: AppColors.mutedInk),
        ),
        const SizedBox(height: 12),
        if (!summary.hasTransactions) ...[
          SoftPanel(
            child: Column(
              children: [
                const Icon(
                  Icons.event_busy_outlined,
                  size: 38,
                  color: AppColors.mutedInk,
                ),
                const SizedBox(height: 10),
                const Text(
                  'No transactions in this period. Try another range or add a transaction.',
                  key: Key('dashboard-empty-period'),
                  textAlign: TextAlign.center,
                ),
                if (summary.hasOlderTransactions) ...[
                  const SizedBox(height: 8),
                  const Text(
                    'You have older activity. Choose Month, Year, or All Time to see it.',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: AppColors.mutedInk, fontSize: 12),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 12),
        ],
        LayoutBuilder(
          builder: (context, constraints) {
            final width = constraints.maxWidth > 720
                ? (constraints.maxWidth - 24) / 3
                : constraints.maxWidth > 440
                ? (constraints.maxWidth - 12) / 2
                : constraints.maxWidth;
            final cards = <Widget>[
              if (summary.hasTransactions) ...[
                SummaryCard(
                  title: 'Expenses $_periodLabel',
                  value: _money(summary.expense),
                  icon: Icons.arrow_downward_rounded,
                  accentColor: AppColors.expense,
                ),
                SummaryCard(
                  title: 'Income $_periodLabel',
                  value: _money(summary.income),
                  icon: Icons.arrow_upward_rounded,
                  accentColor: AppColors.income,
                ),
                SummaryCard(
                  title: summary.net < 0 ? 'Net shortfall' : 'Net cash flow',
                  value: _money(summary.net.abs()),
                  icon: summary.net < 0
                      ? Icons.trending_down
                      : Icons.savings_outlined,
                  subtitle: 'For the selected period',
                  accentColor: summary.net < 0
                      ? AppColors.expense
                      : AppColors.income,
                ),
                SummaryCard(
                  title: 'Transactions $_periodLabel',
                  value: NumberFormat.decimalPattern().format(
                    summary.transactionCount,
                  ),
                  icon: Icons.receipt_long_outlined,
                ),
                SummaryCard(
                  title: 'Top spending area',
                  value: (summary.topCategory ?? 'No expense').replaceAll(
                    '_',
                    ' ',
                  ),
                  icon: Icons.category_outlined,
                  subtitle: _money(summary.topCategoryAmount),
                ),
              ],
              SummaryCard(
                title: summary.cashBalance < 0
                    ? 'All-time cash shortfall'
                    : 'All-time balance',
                value: _money(summary.cashBalance.abs()),
                icon: Icons.account_balance_wallet_outlined,
                subtitle: 'All entered income minus expenses',
                accentColor: summary.cashBalance < 0
                    ? AppColors.expense
                    : AppColors.primary,
              ),
              SummaryCard(
                title: overBudget ? 'Active budget exceeded' : 'Active budget',
                value: summary.hasActiveBudget
                    ? '${summary.activeBudgetPercent.toStringAsFixed(0)}% used'
                    : 'Not set',
                icon: overBudget
                    ? Icons.warning_amber_rounded
                    : Icons.savings_outlined,
                subtitle: summary.hasActiveBudget
                    ? '${_money(summary.activeBudgetSpent)} of ${_money(summary.activeBudgetAmount)}'
                    : 'Create one in Budgets',
                accentColor: overBudget ? AppColors.expense : AppColors.primary,
              ),
            ];
            return Wrap(
              spacing: 12,
              runSpacing: 12,
              children: cards
                  .map(
                    (card) => SizedBox(width: width, height: 170, child: card),
                  )
                  .toList(growable: false),
            );
          },
        ),
      ],
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
                title: result.forecast.forecastMethod == 'v6_reference_lstm'
                    ? 'Weekly estimate · ${DateFormat.MMMd().format(result.forecast.periodStart)}–${DateFormat.MMMd().format(result.forecast.periodEnd)}'
                    : 'Next 7 days',
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
