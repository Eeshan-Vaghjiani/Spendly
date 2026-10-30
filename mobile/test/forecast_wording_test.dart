import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/screens/forecast_detail_screen.dart';
import 'package:spending_support/presentation/widgets/app_version_tile.dart';

void main() {
  testWidgets('version comes from installed package metadata', (tester) async {
    PackageInfo.setMockInitialValues(
      appName: 'Spendly',
      packageName: 'test.spendly',
      version: '9.8.7',
      buildNumber: '42',
      buildSignature: 'fixture',
    );
    await tester.pumpWidget(
      const MaterialApp(home: Scaffold(body: AppVersionTile())),
    );
    await tester.pumpAndSettle();
    expect(find.text('9.8.7 (build 42)'), findsOneWidget);
    expect(find.text('1.1.0'), findsNothing);
  });

  testWidgets(
    'forecast compares recorded spending rather than accuracy percentage',
    (tester) async {
      final forecast = ForecastResult.fromJson({
        'model_version': 'selected-lstm-v6',
        'forecast_method': 'v6_reference_lstm',
        'period_start': '2026-09-14',
        'period_end': '2026-09-20',
        'predicted_spending': 1000,
        'actual_spending': 1400,
        'accuracy_percent': 71.4,
      });
      await tester.pumpWidget(
        MaterialApp(home: ForecastDetailScreen(forecast: forecast)),
      );
      await tester.pumpAndSettle();
      expect(
        find.textContaining('Difference from recorded spending: KES 400'),
        findsOneWidget,
      );
      expect(find.textContaining('actual accuracy'), findsNothing);
      expect(forecast.actualSpending, 1400);
    },
  );
}
