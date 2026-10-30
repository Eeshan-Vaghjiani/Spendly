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
          width: double.infinity,
          child: OutlinedButton.icon(
            key: buttonKey,
            onPressed: loading || !configured ? null : onPressed,
            style: OutlinedButton.styleFrom(
              backgroundColor: Colors.white,
              foregroundColor: const Color(0xFF1F1F1F),
              disabledBackgroundColor: const Color(0xFFF2F2F2),
              disabledForegroundColor: const Color(0xFF747775),
              side: const BorderSide(color: Color(0xFF747775)),
              minimumSize: const Size(48, 48),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
              shape: const StadiumBorder(),
              textStyle: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
            icon: loading
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Image.asset(
                    'assets/branding/google_g.png',
                    width: 20,
                    height: 20,
                    fit: BoxFit.contain,
                    excludeFromSemantics: true,
                  ),
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
