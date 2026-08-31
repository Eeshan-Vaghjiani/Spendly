import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class GoogleAuthSection extends StatelessWidget {
  const GoogleAuthSection({
    required this.buttonKey,
    required this.configured,
    required this.loading,
    required this.onPressed,
    super.key,
  });

  final Key buttonKey;
  final bool configured;
  final bool loading;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Expanded(child: Divider()),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Text('or', style: Theme.of(context).textTheme.bodySmall),
            ),
            const Expanded(child: Divider()),
          ],
        ),
        const SizedBox(height: 16),
        SizedBox(
          height: 48,
          child: OutlinedButton.icon(
            key: buttonKey,
            onPressed: loading || !configured ? null : onPressed,
            icon: loading
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.g_mobiledata, size: 28),
            label: const Text('Continue with Google'),
          ),
        ),
        if (!configured) ...[
          const SizedBox(height: 8),
          const Text(
            'Google sign-in is unavailable in this local build.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.mutedInk, fontSize: 12),
          ),
        ],
      ],
    );
  }
}
