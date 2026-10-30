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
        const Text('Summary updated 22 October 2026'),
        const SizedBox(height: 16),
        const PrivacySummary(),
        const SizedBox(height: 16),
        const Text(
          'Transactions can be entered manually, uploaded as CSV or imported '
          'through optional M-PESA SMS access. SMS import requires its own '
          'disclosure, consent and Android permission; no bank API is connected. You can change your '
          'optional model-improvement choice in Profile and settings.',
        ),
      ],
    ),
  );
}
