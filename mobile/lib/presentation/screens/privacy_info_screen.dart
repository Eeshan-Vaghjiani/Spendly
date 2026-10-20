import 'package:flutter/material.dart';

import '../widgets/privacy_summary.dart';

class PrivacyInfoScreen extends StatelessWidget {
  const PrivacyInfoScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Data and privacy')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          'How Spendly uses your data',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 8),
        const Text('Summary updated 20 October 2026'),
        const SizedBox(height: 16),
        const PrivacySummary(),
        const SizedBox(height: 16),
        const Text(
          'Transactions are entered or uploaded by you. This version does not '
          'connect directly to M-Pesa or a bank account. You can change your '
          'optional model-improvement choice in Profile and settings.',
        ),
      ],
    ),
  );
}
