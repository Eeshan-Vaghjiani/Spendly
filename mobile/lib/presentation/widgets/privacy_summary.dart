import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import 'common.dart';

/// Shared factual summary for setup and the read-only Profile privacy page.
class PrivacySummary extends StatelessWidget {
  const PrivacySummary({super.key});

  @override
  Widget build(BuildContext context) {
    return const SoftPanel(
      padding: EdgeInsets.symmetric(vertical: 6),
      child: Column(
        children: [
          _DataUseRow(
            icon: Icons.folder_open_outlined,
            title: 'What we use',
            text: 'Your name, email, transactions, income entries and budgets.',
          ),
          Divider(height: 1, indent: 58),
          _DataUseRow(
            icon: Icons.auto_graph_outlined,
            title: 'Why we use it',
            text:
                'To create your forecasts, spending checks and recommendations.',
          ),
          Divider(height: 1, indent: 58),
          _DataUseRow(
            icon: Icons.settings_suggest_outlined,
            title: 'How and where',
            text:
                'The backend processes it and stores it with your account in the service database.',
          ),
          Divider(height: 1, indent: 58),
          _DataUseRow(
            icon: Icons.people_outline,
            title: 'Who can see it',
            text:
                'Other app users cannot see your financial records. Authorized administrators can inspect and correct account records, transactions and budgets for support. Support record views, exports and successful changes are audited.',
          ),
          Divider(height: 1, indent: 58),
          _DataUseRow(
            icon: Icons.login,
            title: 'Sign-in history',
            text:
                'Successful registration and sign-ins record the time and sign-in method for administrator support. This does not show whether you are online or track your device or location.',
          ),
          Divider(height: 1, indent: 58),
          _DataUseRow(
            icon: Icons.sms_outlined,
            title: 'Optional M-PESA import',
            text:
                'SMS import requires separate consent and Android permission. Only normalized financial details are synchronized. Source identities and original import audit details remain after transaction deletion to prevent duplicates and check reversals.',
          ),
          Divider(height: 1, indent: 58),
          _DataUseRow(
            icon: Icons.delete_outline,
            title: 'Your control',
            text:
                'You can correct or delete transactions and budgets from the app. Future model-improvement permission is optional; your records are not automatically used for training.',
          ),
        ],
      ),
    );
  }
}

class _DataUseRow extends StatelessWidget {
  const _DataUseRow({
    required this.icon,
    required this.title,
    required this.text,
  });

  final IconData icon;
  final String title;
  final String text;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primary),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text(text),
    );
  }
}
