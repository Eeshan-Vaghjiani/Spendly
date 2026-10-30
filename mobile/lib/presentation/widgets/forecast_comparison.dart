import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/reporting_time.dart';
import '../../core/theme/app_theme.dart';
import 'common.dart';

class ForecastComparison extends StatelessWidget {
  const ForecastComparison({
    super.key,
    required this.estimate,
    required this.actual,
  });
  final double estimate;
  final double actual;

  @override
  Widget build(BuildContext context) {
    final maximum = math.max(estimate, actual);
    final money = NumberFormat.currency(symbol: 'KES ', decimalDigits: 2);
    return Column(
      children: [
        for (final (label, value, color) in [
          ('Estimate', estimate, AppColors.primary),
          ('Recorded', actual, const Color(0xFF476EB1)),
        ])
          Padding(
            padding: const EdgeInsets.only(top: 14),
            child: Semantics(
              label: '$label: ${money.format(value)}',
              child: ExcludeSemantics(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Wrap(
                      alignment: WrapAlignment.spaceBetween,
                      spacing: 12,
                      runSpacing: 4,
                      children: [
                        Text(label),
                        Text(
                          money.format(value),
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                      ],
                    ),
                    const SizedBox(height: 7),
                    LinearProgressIndicator(
                      value: maximum > 0 ? (value / maximum).clamp(0, 1) : 0,
                      color: color,
                      minHeight: 9,
                      borderRadius: BorderRadius.circular(8),
                      backgroundColor: AppColors.mint.withValues(alpha: .35),
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class ForecastHistoryPanel extends StatefulWidget {
  const ForecastHistoryPanel({super.key, required this.load});
  final Future<List<Map<String, dynamic>>> Function() load;
  @override
  State<ForecastHistoryPanel> createState() => _ForecastHistoryPanelState();
}

class _ForecastHistoryPanelState extends State<ForecastHistoryPanel> {
  late Future<List<Map<String, dynamic>>> _future;
  @override
  void initState() {
    super.initState();
    _future = widget.load();
  }

  @override
  Widget build(BuildContext context) => SoftPanel(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Previous completed weeks',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        FutureBuilder<List<Map<String, dynamic>>>(
          future: _future,
          builder: (context, snapshot) {
            if (snapshot.connectionState != ConnectionState.done) {
              return const Padding(
                padding: EdgeInsets.all(16),
                child: Center(child: CircularProgressIndicator()),
              );
            }
            if (snapshot.hasError) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Could not load saved forecast comparisons.'),
                  TextButton(
                    onPressed: () => setState(() {
                      _future = widget.load();
                    }),
                    child: const Text('Retry history'),
                  ),
                ],
              );
            }
            final today = nairobiDate(DateTime.now());
            final seen = <String>{};
            final rows = (snapshot.data ?? const <Map<String, dynamic>>[])
                .where((row) {
                  final end = DateTime.tryParse(
                    row['period_end']?.toString() ?? '',
                  );
                  if (end == null ||
                      !calendarDate(end).isBefore(today) ||
                      row['actual_spending'] is! num ||
                      row['predicted_spending'] is! num) {
                    return false;
                  }
                  return seen.add(
                    '${row['period_start']}/${row['period_end']}',
                  );
                })
                .take(4)
                .toList();
            if (rows.isEmpty) {
              return const Text(
                'No completed recorded comparisons yet. Pending weeks are not shown as zero.',
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Latest saved estimate for each completed week. Missing entries can affect recorded spending.',
                  style: TextStyle(color: AppColors.mutedInk),
                ),
                for (final row in rows)
                  Padding(
                    padding: const EdgeInsets.only(top: 16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${row['period_start']} – ${row['period_end']}',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        ForecastComparison(
                          estimate: (row['predicted_spending'] as num)
                              .toDouble(),
                          actual: (row['actual_spending'] as num).toDouble(),
                        ),
                      ],
                    ),
                  ),
              ],
            );
          },
        ),
      ],
    ),
  );
}
