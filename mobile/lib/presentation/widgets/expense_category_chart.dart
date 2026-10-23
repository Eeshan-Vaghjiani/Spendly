import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_theme.dart';
import '../../data/models/models.dart';
import 'common.dart';

/// Direct labels keep the chart readable without colours, hover or a legend.
class ExpenseCategoryChart extends StatelessWidget {
  const ExpenseCategoryChart({
    super.key,
    required this.items,
    required this.range,
    this.available = true,
    this.onDetails,
  });
  final List<ExpenseCategory> items;
  final String range;
  final bool available;
  final VoidCallback? onDetails;

  @override
  Widget build(BuildContext context) {
    final positive = items.where((item) => item.amount > 0).toList()
      ..sort((a, b) => b.amount.compareTo(a.amount));
    final money = NumberFormat.currency(symbol: 'KES ', decimalDigits: 2);
    // Bound the dashboard height without losing any amount from the chart.
    final visible = positive.take(4).toList();
    if (positive.length > 4) {
      visible.add(
        ExpenseCategory(
          category: 'Other categories',
          amount: positive
              .skip(4)
              .fold<double>(0, (sum, item) => sum + item.amount),
        ),
      );
    }
    final maximum = visible.fold<double>(
      0,
      (max, item) => item.amount > max ? item.amount : max,
    );
    return SoftPanel(
      key: const Key('expense-category-chart'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 4,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(
                'Expenses by category',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              if (onDetails != null)
                TextButton(
                  key: const Key('dashboard-view-analytics'),
                  onPressed: onDetails,
                  child: const Text('Analytics'),
                ),
            ],
          ),
          const SizedBox(height: 4),
          Text(range, style: const TextStyle(color: AppColors.mutedInk)),
          if (!available) ...[
            const SizedBox(height: 12),
            const Text(
              'Category breakdown is unavailable. Try refreshing later.',
            ),
          ] else if (visible.isEmpty) ...[
            const SizedBox(height: 12),
            const Text('No recorded expenses in this period.'),
          ],
          for (final item in visible)
            Padding(
              key: ValueKey('expense-category-${item.category}'),
              padding: const EdgeInsets.only(top: 16),
              child: Semantics(
                label:
                    '${item.category.replaceAll('_', ' ')}: ${money.format(item.amount)}',
                child: ExcludeSemantics(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        alignment: WrapAlignment.spaceBetween,
                        spacing: 12,
                        runSpacing: 4,
                        children: [
                          Text(item.category.replaceAll('_', ' ')),
                          Text(
                            money.format(item.amount),
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                        ],
                      ),
                      const SizedBox(height: 7),
                      LinearProgressIndicator(
                        value: maximum > 0 ? item.amount / maximum : 0,
                        minHeight: 7,
                        borderRadius: BorderRadius.circular(8),
                        color: AppColors.primary,
                        backgroundColor: AppColors.mint.withValues(alpha: .35),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
