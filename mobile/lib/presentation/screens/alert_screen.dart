import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../data/models/models.dart';
import '../widgets/common.dart';

class AlertScreen extends StatelessWidget {
  const AlertScreen({super.key, required this.alerts});

  final List<AlertResult> alerts;

  @override
  Widget build(BuildContext context) {
    final unusual = alerts.where((alert) => alert.isUnusualSpending).toList();
    return Scaffold(
      appBar: AppBar(title: const Text('Spending check')),
      body: unusual.isEmpty
          ? ListView(
              padding: const EdgeInsets.all(20),
              children: [
                SoftPanel(
                  child: Column(
                    children: [
                      Container(
                        width: 76,
                        height: 76,
                        decoration: BoxDecoration(
                          color: AppColors.mint.withValues(alpha: 0.55),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.check_rounded,
                          color: AppColors.primary,
                          size: 42,
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Everything looks usual',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 6),
                      const Text(
                        'The latest check did not find a spending entry that '
                        'needs your attention.',
                        textAlign: TextAlign.center,
                      ),
                    ],
                  ),
                ),
              ],
            )
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
              children: [
                SoftPanel(
                  backgroundColor: const Color(0xFFFFF5E5),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Icon(
                        Icons.search_rounded,
                        color: Color(0xFF8C5A00),
                        size: 32,
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              unusual.length == 1
                                  ? 'One item is worth a look'
                                  : '${unusual.length} items are worth a look',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: 5),
                            const Text(
                              'This does not mean fraud. It only means the entry '
                              'looks different from your recent pattern.',
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                for (var index = 0; index < unusual.length; index++) ...[
                  SoftPanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        StatusPill(
                          label: 'Check ${index + 1}',
                          color: const Color(0xFF8C5A00),
                          icon: Icons.visibility_outlined,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          _friendlyExplanation(unusual[index].explanation),
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 10),
                        const Text(
                          'Compare it with your receipt or transaction history. '
                          'If the entry is correct, you do not need to do anything.',
                        ),
                      ],
                    ),
                  ),
                  if (index != unusual.length - 1) const SizedBox(height: 14),
                ],
              ],
            ),
    );
  }

  static String _friendlyExplanation(String? explanation) {
    final text = explanation?.trim() ?? '';
    final technical =
        text.toLowerCase().contains('heuristic') ||
        text.toLowerCase().contains('threshold') ||
        text.contains('=');
    if (text.isEmpty || technical) {
      return 'This entry is different from what you usually record.';
    }
    return text;
  }
}
