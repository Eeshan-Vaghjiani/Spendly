import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../widgets/brand_logo.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.cream, AppColors.canvas, Color(0xFFE4F1EC)],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: Semantics(
              label: 'Loading Spendly',
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  BrandLogo(size: 126),
                  SizedBox(height: 24),
                  Text(
                    'Spendly',
                    style: TextStyle(
                      color: AppColors.ink,
                      fontSize: 28,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -0.5,
                    ),
                  ),
                  SizedBox(height: 8),
                  Text(
                    'Clearer choices, one step at a time',
                    style: TextStyle(color: AppColors.mutedInk),
                  ),
                  SizedBox(height: 34),
                  SizedBox(
                    width: 28,
                    height: 28,
                    child: CircularProgressIndicator(strokeWidth: 2.6),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
