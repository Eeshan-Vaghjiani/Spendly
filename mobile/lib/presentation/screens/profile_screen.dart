import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../controllers/providers.dart';
import '../widgets/common.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final user = auth.user;
    return Scaffold(
      appBar: AppBar(title: const Text('Profile and settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SoftPanel(
            child: Column(
              children: [
                CircleAvatar(
                  radius: 36,
                  backgroundColor: AppColors.mint,
                  child: Text(
                    user?.displayName.substring(0, 1).toUpperCase() ?? '?',
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      color: AppColors.primaryDark,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  user?.displayName ?? '',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                Text(
                  user?.email ?? '',
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: AppColors.mutedInk),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          const ListTile(
            leading: Icon(Icons.verified_user_outlined),
            title: Text('Account security'),
            subtitle: Text(
              'Your sign-in token is stored in secure device storage.',
            ),
          ),
          const ListTile(
            leading: Icon(Icons.privacy_tip_outlined),
            title: Text('Privacy'),
            subtitle: Text(
              'Transactions are entered or uploaded by you. This version does '
              'not connect directly to M-Pesa or a bank account.',
            ),
          ),
          SwitchListTile(
            secondary: const Icon(Icons.model_training_outlined),
            title: const Text('Future model improvement'),
            subtitle: const Text(
              'Optional permission for future de-identified model training. '
              'This does not affect your access to the app.',
            ),
            value: user?.modelTrainingOptIn ?? false,
            onChanged: auth.loading
                ? null
                : (value) async {
                    final saved = await ref
                        .read(authControllerProvider.notifier)
                        .updateConsent(modelTrainingOptIn: value);
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            saved
                                ? 'Your model-improvement choice was saved.'
                                : 'Could not save your choice.',
                          ),
                        ),
                      );
                    }
                  },
          ),
          const ListTile(
            leading: Icon(Icons.info_outline),
            title: Text('Decision-support disclaimer'),
            subtitle: Text(
              'Insights are planning support, not professional financial advice '
              'or fraud findings.',
            ),
          ),
          const ListTile(
            leading: Icon(Icons.info_outline),
            title: Text('App version'),
            subtitle: Text('1.1.0'),
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: () async {
              await ref.read(authControllerProvider.notifier).logout();
              if (context.mounted) {
                Navigator.of(context).popUntil((route) => route.isFirst);
              }
            },
            icon: const Icon(Icons.logout),
            label: const Text('Sign out'),
          ),
        ],
      ),
    );
  }
}
