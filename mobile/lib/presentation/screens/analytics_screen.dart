import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_theme.dart';
import '../../data/models/models.dart';
import '../controllers/providers.dart';
import '../widgets/common.dart';

enum _ChartMetric { cashflow, income, expense, net }

class AnalyticsScreen extends ConsumerStatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  ConsumerState<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends ConsumerState<AnalyticsScreen> {
  String _resolution = 'monthly';
  _ChartMetric _metric = _ChartMetric.cashflow;
  late Future<CashflowAnalytics> _future;

  static const _resolutions = <String, String>{
    'daily': 'Daily',
    'weekly': 'Weekly',
    'monthly': 'Monthly',
    'quarterly': '3 months',
    'yearly': 'Yearly',
  };

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _future = ref.read(repositoryProvider).cashflowAnalytics(_resolution);
  }

  void _selectResolution(String value) {
    if (value == _resolution) return;
    setState(() {
      _resolution = value;
      _reload();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Analytics'),
        actions: [
          IconButton(
            tooltip: 'Refresh analytics',
            onPressed: () => setState(_reload),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: FutureBuilder<CashflowAnalytics>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return ErrorPanel(
              message: snapshot.error.toString(),
              onRetry: () => setState(_reload),
            );
          }
          final analytics = snapshot.requireData;
          return RefreshIndicator(
            onRefresh: () async {
              setState(_reload);
              await _future;
            },
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
              children: [
                Text(
                  'See where your money goes',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 5),
                Text(
                  'Compare money in, money out, and what remains over time.',
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: AppColors.mutedInk),
                ),
                const SizedBox(height: 18),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: _resolutions.entries
                        .map((entry) {
                          return Padding(
                            padding: const EdgeInsets.only(right: 8),
                            child: ChoiceChip(
                              label: Text(entry.value),
                              selected: _resolution == entry.key,
                              onSelected: (_) => _selectResolution(entry.key),
                            ),
                          );
                        })
                        .toList(growable: false),
                  ),
                ),
                const SizedBox(height: 16),
                _SummaryGrid(summary: analytics.summary),
                const SizedBox(height: 16),
                SoftPanel(
                  padding: const EdgeInsets.fromLTRB(14, 18, 14, 12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              'Cash-flow trend',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                          ),
                          Text(
                            '${DateFormat.yMMMd().format(analytics.periodStart)} – '
                            '${DateFormat.yMMMd().format(analytics.periodEnd)}',
                            style: Theme.of(context).textTheme.bodySmall
                                ?.copyWith(color: AppColors.mutedInk),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 7,
                        runSpacing: 7,
                        children: [
                          _MetricChip(
                            label: 'Income + expense',
                            selected: _metric == _ChartMetric.cashflow,
                            onTap: () =>
                                setState(() => _metric = _ChartMetric.cashflow),
                          ),
                          _MetricChip(
                            label: 'Income',
                            selected: _metric == _ChartMetric.income,
                            onTap: () =>
                                setState(() => _metric = _ChartMetric.income),
                          ),
                          _MetricChip(
                            label: 'Expenses',
                            selected: _metric == _ChartMetric.expense,
                            onTap: () =>
                                setState(() => _metric = _ChartMetric.expense),
                          ),
                          _MetricChip(
                            label: 'Net saved',
                            selected: _metric == _ChartMetric.net,
                            onTap: () =>
                                setState(() => _metric = _ChartMetric.net),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),
                      if (analytics.series.every(
                        (item) => item.income == 0 && item.expense == 0,
                      ))
                        const SizedBox(
                          height: 245,
                          child: EmptyPanel(
                            icon: Icons.show_chart,
                            message:
                                'Add income or expenses to draw your first graph.',
                          ),
                        )
                      else
                        SizedBox(
                          height: 270,
                          width: double.infinity,
                          child: CustomPaint(
                            painter: _CashflowPainter(
                              points: analytics.series,
                              metric: _metric,
                            ),
                          ),
                        ),
                      if (_metric == _ChartMetric.cashflow) ...[
                        const SizedBox(height: 4),
                        const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            _LegendDot(
                              label: 'Income',
                              color: AppColors.income,
                            ),
                            SizedBox(width: 18),
                            _LegendDot(
                              label: 'Expense',
                              color: AppColors.expense,
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                _PeriodBreakdown(points: analytics.series),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _SummaryGrid extends StatelessWidget {
  const _SummaryGrid({required this.summary});

  final CashflowSummary summary;

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat.currency(symbol: 'KES ', decimalDigits: 0);
    return LayoutBuilder(
      builder: (context, constraints) {
        final cardWidth = constraints.maxWidth > 720
            ? (constraints.maxWidth - 36) / 4
            : (constraints.maxWidth - 12) / 2;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            SizedBox(
              width: cardWidth,
              height: 190,
              child: SummaryCard(
                title: 'Cash balance',
                value: money.format(summary.cashBalance),
                subtitle: 'All income minus all expenses',
                icon: Icons.account_balance_wallet_outlined,
                accentColor: summary.cashBalance < 0
                    ? AppColors.expense
                    : AppColors.primary,
              ),
            ),
            SizedBox(
              width: cardWidth,
              height: 190,
              child: SummaryCard(
                title: 'Income in period',
                value: money.format(summary.income),
                icon: Icons.south_west_rounded,
                accentColor: AppColors.income,
              ),
            ),
            SizedBox(
              width: cardWidth,
              height: 190,
              child: SummaryCard(
                title: 'Spent in period',
                value: money.format(summary.expense),
                icon: Icons.north_east_rounded,
                accentColor: AppColors.expense,
              ),
            ),
            SizedBox(
              width: cardWidth,
              height: 190,
              child: SummaryCard(
                title: summary.net < 0 ? 'Period shortfall' : 'Saved in period',
                value: money.format(summary.net.abs()),
                subtitle: summary.income > 0
                    ? '${summary.savingsRate.toStringAsFixed(0)}% savings rate'
                    : 'Add income to calculate savings',
                icon: summary.net < 0
                    ? Icons.trending_down
                    : Icons.savings_outlined,
                accentColor: summary.net < 0
                    ? AppColors.expense
                    : AppColors.primary,
              ),
            ),
          ],
        );
      },
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return FilterChip(
      label: Text(label),
      selected: selected,
      onSelected: (_) => onTap(),
      showCheckmark: false,
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 5),
        Text(label, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}

class _PeriodBreakdown extends StatelessWidget {
  const _PeriodBreakdown({required this.points});

  final List<CashflowPoint> points;

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat.currency(symbol: 'KES ', decimalDigits: 0);
    final recent = points.reversed.take(6).toList(growable: false);
    return SoftPanel(
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 18, 18, 8),
            child: Text(
              'Recent period breakdown',
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
          for (final point in recent)
            ListTile(
              title: Text(point.label),
              subtitle: Text(
                'In ${money.format(point.income)} · Out ${money.format(point.expense)}',
              ),
              trailing: Text(
                '${point.net < 0 ? '−' : '+'}${money.format(point.net.abs())}',
                style: TextStyle(
                  color: point.net < 0 ? AppColors.expense : AppColors.income,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

class _CashflowPainter extends CustomPainter {
  const _CashflowPainter({required this.points, required this.metric});

  final List<CashflowPoint> points;
  final _ChartMetric metric;

  List<double> _values(_ChartMetric selected) => switch (selected) {
    _ChartMetric.income => points.map((item) => item.income).toList(),
    _ChartMetric.expense => points.map((item) => item.expense).toList(),
    _ChartMetric.net => points.map((item) => item.net).toList(),
    _ChartMetric.cashflow =>
      points.expand((item) => [item.income, item.expense]).toList(),
  };

  @override
  void paint(Canvas canvas, Size size) {
    const left = 8.0;
    const right = 8.0;
    const top = 12.0;
    const bottom = 38.0;
    final graphWidth = size.width - left - right;
    final graphHeight = size.height - top - bottom;
    final values = _values(metric);
    final minimum = math.min(0.0, values.reduce(math.min));
    final maximum = math.max(0.0, values.reduce(math.max));
    final spread = math.max(1.0, maximum - minimum);
    final paddedMinimum = minimum < 0 ? minimum - spread * .08 : 0.0;
    final paddedMaximum = maximum + spread * .1;

    final gridPaint = Paint()
      ..color = AppColors.outline.withValues(alpha: .72)
      ..strokeWidth = 1;
    for (var index = 0; index <= 4; index++) {
      final y = top + graphHeight * index / 4;
      canvas.drawLine(
        Offset(left, y),
        Offset(size.width - right, y),
        gridPaint,
      );
    }

    Offset position(int index, double value) {
      final x = points.length == 1
          ? left + graphWidth / 2
          : left + graphWidth * index / (points.length - 1);
      final y =
          top +
          (paddedMaximum - value) /
              (paddedMaximum - paddedMinimum) *
              graphHeight;
      return Offset(x, y);
    }

    if (minimum < 0) {
      final zeroY = position(0, 0).dy;
      canvas.drawLine(
        Offset(left, zeroY),
        Offset(size.width - right, zeroY),
        Paint()
          ..color = AppColors.mutedInk
          ..strokeWidth = 1.3,
      );
    }

    void drawSeries(List<double> series, Color color) {
      final offsets = [
        for (var index = 0; index < series.length; index++)
          position(index, series[index]),
      ];
      final path = Path()..moveTo(offsets.first.dx, offsets.first.dy);
      for (var index = 0; index < offsets.length - 1; index++) {
        final current = offsets[index];
        final next = offsets[index + 1];
        final middle = (current.dx + next.dx) / 2;
        path.cubicTo(middle, current.dy, middle, next.dy, next.dx, next.dy);
      }
      canvas.drawPath(
        path,
        Paint()
          ..color = color
          ..strokeWidth = 3
          ..strokeCap = StrokeCap.round
          ..style = PaintingStyle.stroke,
      );
      for (final offset in offsets) {
        canvas.drawCircle(offset, 3.2, Paint()..color = color);
      }
    }

    switch (metric) {
      case _ChartMetric.cashflow:
        drawSeries(
          points.map((item) => item.income).toList(),
          AppColors.income,
        );
        drawSeries(
          points.map((item) => item.expense).toList(),
          AppColors.expense,
        );
      case _ChartMetric.income:
        drawSeries(
          points.map((item) => item.income).toList(),
          AppColors.income,
        );
      case _ChartMetric.expense:
        drawSeries(
          points.map((item) => item.expense).toList(),
          AppColors.expense,
        );
      case _ChartMetric.net:
        drawSeries(
          points.map((item) => item.net).toList(),
          points.last.net < 0 ? AppColors.expense : AppColors.primary,
        );
    }

    final labelEvery = math.max(1, (points.length / 4).ceil());
    for (var index = 0; index < points.length; index++) {
      if (index % labelEvery != 0 && index != points.length - 1) continue;
      final text = TextPainter(
        text: TextSpan(
          text: points[index].label,
          style: const TextStyle(fontSize: 10, color: AppColors.mutedInk),
        ),
        textDirection: ui.TextDirection.ltr,
      )..layout(maxWidth: 75);
      final x = position(index, 0).dx;
      text.paint(
        canvas,
        Offset(
          (x - text.width / 2).clamp(0, size.width - text.width),
          size.height - bottom + 13,
        ),
      );
    }
  }

  @override
  bool shouldRepaint(covariant _CashflowPainter oldDelegate) {
    return oldDelegate.points != points || oldDelegate.metric != metric;
  }
}
