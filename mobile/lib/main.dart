import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/theme/app_theme.dart';
import 'presentation/controllers/providers.dart';
import 'presentation/screens/home_shell.dart';
import 'presentation/screens/consent_setup_screen.dart';
import 'presentation/screens/register_screen.dart';
import 'presentation/screens/onboarding_screen.dart';
import 'presentation/screens/splash_screen.dart';

void main() {
  runApp(const ProviderScope(child: SpendlyApp()));
}

class SpendlyApp extends ConsumerWidget {
  const SpendlyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    return MaterialApp(
      title: 'Spendly',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      home: !auth.initialized
          ? const SplashScreen()
          : auth.user == null
          ? const RegisterScreen(isRoot: true)
          : !auth.user!.hasRequiredConsents
          ? const ConsentSetupScreen()
          : !auth.user!.onboardingCompleted
          ? const OnboardingScreen()
          : HomeShell(key: ValueKey(auth.user!.id)),
    );
  }
}
