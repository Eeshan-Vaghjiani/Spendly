import 'package:flutter/material.dart';

import '../widgets/common.dart';
import 'analysis_history_screen.dart';
import 'profile_screen.dart';
import 'transaction_upload_screen.dart';

class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('More')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          SoftPanel(
            padding: EdgeInsets.zero,
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.upload_file_outlined),
                  title: const Text('Import transactions'),
                  subtitle: const Text('Add several entries from a CSV file.'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const TransactionUploadScreen(),
                    ),
                  ),
                ),
                const Divider(height: 1, indent: 56),
                ListTile(
                  leading: const Icon(Icons.history_rounded),
                  title: const Text('Past insights'),
                  subtitle: const Text('Review earlier forecasts and checks.'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const AnalysisHistoryScreen(),
                    ),
                  ),
                ),
                const Divider(height: 1, indent: 56),
                ListTile(
                  key: const Key('open-profile'),
                  leading: const Icon(Icons.person_outline),
                  title: const Text('Profile and settings'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const ProfileScreen(),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
