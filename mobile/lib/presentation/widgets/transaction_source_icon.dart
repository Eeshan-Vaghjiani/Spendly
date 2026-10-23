import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class TransactionSourceIcon extends StatelessWidget {
  const TransactionSourceIcon({super.key, required this.source});

  final String source;

  @override
  Widget build(BuildContext context) {
    final (icon, label, description) = switch (source) {
      'mpesa_sms' => (
        Icons.sms_outlined,
        'Imported from M-PESA SMS',
        'Imported from a supported transaction message on your phone. Editing this entry keeps its original source.',
      ),
      'manual' => (
        Icons.edit_outlined,
        'Added manually',
        'Entered using Add transaction.',
      ),
      'csv_upload' => (
        Icons.description_outlined,
        'Imported from CSV',
        'Created by a CSV upload.',
      ),
      'admin' => (
        Icons.support_agent_outlined,
        'Added by support',
        'Added through the administrator tools.',
      ),
      _ => (
        Icons.help_outline,
        'Source unavailable',
        'The source could not be identified. It is not assumed to be manual.',
      ),
    };
    return IconButton(
      key: ValueKey('transaction-source-$source'),
      tooltip: label,
      icon: Icon(icon, size: 16, color: AppColors.mutedInk),
      onPressed: () => showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          title: Text(label),
          content: Text(description),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            ),
          ],
        ),
      ),
    );
  }
}
