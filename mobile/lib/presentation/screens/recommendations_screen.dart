import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../data/models/models.dart';
import '../widgets/common.dart';

class RecommendationsScreen extends StatelessWidget {
  const RecommendationsScreen({super.key, required this.recommendations});

  final List<RecommendationResult> recommendations;

  static int _severityRank(String severity) => switch (severity) {
    'critical' => 4,
    'high' => 3,
    'warning' => 2,
    _ => 1,
  };

  @override
  Widget build(BuildContext context) {
    final sorted = [...recommendations]
      ..sort(
        (left, right) => _severityRank(
          right.severity,
        ).compareTo(_severityRank(left.severity)),
      );
    final visible = sorted.take(3).toList(growable: false);

    return Scaffold(
      appBar: AppBar(title: const Text('Your next steps')),
      body: visible.isEmpty
          ? const EmptyPanel(
              icon: Icons.eco_outlined,
              message: 'You have no new action to take right now.',
            )
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
              children: [
                SoftPanel(
                  backgroundColor: AppColors.primary,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.lightbulb_outline_rounded,
                        color: Colors.white,
                        size: 30,
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Keep it simple',
                              style: Theme.of(context).textTheme.titleMedium
                                  ?.copyWith(color: Colors.white),
                            ),
                            const SizedBox(height: 4),
                            const Text(
                              'Start with the first step. The others can wait.',
                              style: TextStyle(
                                color: Color(0xFFE7F5F0),
                                height: 1.4,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                for (var index = 0; index < visible.length; index++) ...[
                  _RecommendationCard(
                    item: visible[index],
                    index: index,
                    total: visible.length,
                  ),
                  if (index != visible.length - 1) const SizedBox(height: 14),
                ],
                const SizedBox(height: 20),
                Text(
                  'These are planning suggestions based on the information in '
                  'the app. You decide what fits your situation.',
                  textAlign: TextAlign.center,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: AppColors.mutedInk),
                ),
              ],
            ),
    );
  }
}

class _RecommendationCard extends StatelessWidget {
  const _RecommendationCard({
    required this.item,
    required this.index,
    required this.total,
  });

  final RecommendationResult item;
  final int index;
  final int total;

  @override
  Widget build(BuildContext context) {
    final isFirst = index == 0;
    final accent = isFirst ? AppColors.primary : AppColors.mutedInk;
    return SoftPanel(
      semanticLabel: '${isFirst ? 'Start here. ' : ''}${item.title}',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              StatusPill(
                label: isFirst ? 'Start here' : 'Later',
                color: accent,
                icon: isFirst ? Icons.arrow_forward_rounded : Icons.schedule,
              ),
              const Spacer(),
              Text(
                '${index + 1} of $total',
                style: Theme.of(
                  context,
                ).textTheme.labelMedium?.copyWith(color: AppColors.mutedInk),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(item.title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 14),
          Text(
            'Try this',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: AppColors.primary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 5),
          Text(item.suggestedAction),
          const SizedBox(height: 10),
          TextButton.icon(
            onPressed: () => _showDetails(context),
            icon: const Icon(Icons.info_outline, size: 18),
            label: const Text('Why am I seeing this?'),
          ),
        ],
      ),
    );
  }

  void _showDetails(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(22, 8, 22, 28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(item.title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              Text(item.message),
              if (item.reason.isNotEmpty) ...[
                const SizedBox(height: 14),
                Text(
                  'Based on',
                  style: Theme.of(
                    context,
                  ).textTheme.labelLarge?.copyWith(color: AppColors.primary),
                ),
                const SizedBox(height: 4),
                Text(item.reason),
              ],
              if (item.disclaimer.isNotEmpty) ...[
                const SizedBox(height: 16),
                Text(
                  item.disclaimer,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: AppColors.mutedInk),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
