import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_theme.dart';
import '../../data/models/models.dart';
import '../widgets/common.dart';

class ForecastDetailScreen extends StatelessWidget {
  const ForecastDetailScreen({super.key, required this.forecast});

  final ForecastResult forecast;

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat.currency(symbol: 'KES ', decimalDigits: 0);
    final date = DateFormat.MMMd();
    return Scaffold(
      appBar: AppBar(title: const Text('Weekly spending estimate')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          SoftPanel(
            backgroundColor: AppColors.primary,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const StatusPill(
                  label: 'Estimated spending',
                  color: Colors.white,
                  icon: Icons.auto_graph_rounded,
                ),
                const SizedBox(height: 20),
                Text(
                  money.format(forecast.predictedSpending),
                  key: const Key('forecast-value'),
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    color: Colors.white,
                    fontSize: 34,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '${date.format(forecast.periodStart)} – '
                  '${date.format(forecast.periodEnd)}',
                  style: const TextStyle(color: Color(0xFFE7F5F0)),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          SoftPanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        'History available',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    Text(
                      '${forecast.dataReadinessPercent}%',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: AppColors.primary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                LinearProgressIndicator(
                  value: forecast.dataReadinessPercent / 100,
                  minHeight: 9,
                  borderRadius: BorderRadius.circular(99),
                ),
                const SizedBox(height: 10),
                Text(
                  'Week ${forecast.historyWeeks} of '
                  '${forecast.requiredHistoryWeeks} · '
                  '${forecast.confidenceLabel}',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 5),
                Text(
                  forecast.forecastMethod == 'personal_spending_baseline'
                      ? 'This early estimate uses your recent weekly average. '
                            'Each added week makes it more representative.'
                      : forecast.forecastMethod == 'v6_reference_lstm'
                      ? 'This LSTM estimate uses recorded history before the displayed week. It is not a rolling next-seven-days forecast.'
                      : 'Eight weeks are available, so the trained model and '
                            'its stronger linear comparator are blended.',
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          SoftPanel(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.fact_check_outlined, color: AppColors.primary),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        forecast.accuracyPercent == null
                            ? 'Accuracy pending'
                            : '${forecast.accuracyPercent!.toStringAsFixed(0)}% actual accuracy',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(forecast.accuracyNote),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          SoftPanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'How to use this',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 8),
                const Text(
                  'Use this amount as a planning guide for the week. Compare it '
                  'with your budget and adjust optional spending if needed.',
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          ExpansionTile(
            tilePadding: const EdgeInsets.symmetric(horizontal: 6),
            title: const Text('About this estimate'),
            subtitle: const Text('Model details and limitations'),
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(6, 0, 6, 16),
                child: Text(
                  'This experimental estimate uses your recorded spending '
                  'pattern and model ${forecast.modelVersion}. The model was '
                  'validated on synthetic development data, so data readiness '
                  'is not the same as accuracy. It is not a guaranteed outcome '
                  'or professional financial advice.',
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: AppColors.mutedInk),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
