import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/core/theme/app_theme.dart';
import 'package:spending_support/presentation/widgets/google_auth_section.dart';

void main() {
  for (final textScale in [1.0, 2.0]) {
    testWidgets(
      'Google action remains visible and usable at scale $textScale',
      (tester) async {
        tester.view.physicalSize = const Size(320, 640);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final semantics = tester.ensureSemantics();
        var taps = 0;
        try {
          await tester.pumpWidget(
            MaterialApp(
              theme: AppTheme.light(),
              home: Scaffold(
                body: MediaQuery(
                  data: MediaQueryData(
                    textScaler: TextScaler.linear(textScale),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: GoogleAuthSection(
                      buttonKey: const Key('test-google'),
                      configured: true,
                      loading: false,
                      onPressed: () => taps++,
                    ),
                  ),
                ),
              ),
            ),
          );
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull);
          final button = tester.widget<OutlinedButton>(
            find.byKey(const Key('test-google')),
          );
          expect(button.style!.backgroundColor!.resolve({}), Colors.white);
          expect(
            button.style!.foregroundColor!.resolve({}),
            const Color(0xFF1F1F1F),
          );
          final icon = tester.widget<Image>(find.byType(Image));
          expect(
            (icon.image as AssetImage).assetName,
            'assets/branding/google_g.png',
          );
          expect(icon.color, isNull);
          expect(icon.excludeFromSemantics, true);
          expect(find.byIcon(Icons.g_mobiledata), findsNothing);
          await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
          await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
          await expectLater(tester, meetsGuideline(textContrastGuideline));
          await tester.tap(find.byKey(const Key('test-google')));
          expect(taps, 1);
        } finally {
          semantics.dispose();
        }
      },
    );
  }

  for (final loading in [false, true]) {
    testWidgets(
      'Google action blocks taps when ${loading ? 'busy' : 'unconfigured'}',
      (tester) async {
        var taps = 0;
        await tester.pumpWidget(
          MaterialApp(
            theme: AppTheme.light(),
            home: Scaffold(
              body: GoogleAuthSection(
                buttonKey: const Key('test-google'),
                configured: loading,
                loading: loading,
                onPressed: () => taps++,
              ),
            ),
          ),
        );
        await tester.pump();
        final button = tester.widget<OutlinedButton>(
          find.byKey(const Key('test-google')),
        );
        expect(button.onPressed, isNull);
        await tester.tap(find.byKey(const Key('test-google')));
        await tester.pump();
        expect(taps, 0);
        expect(find.text('Continue with Google'), findsOneWidget);
        if (loading) {
          expect(find.byType(CircularProgressIndicator), findsOneWidget);
        } else {
          expect(
            find.text('Google sign-in is unavailable in this local build.'),
            findsOneWidget,
          );
        }
      },
    );
  }
}
