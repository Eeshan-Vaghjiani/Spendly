import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/controllers/providers.dart';

import 'widget_test.dart' show FakeGoogleIdentity, FakeRepository;

const _firstAccount = UserProfile(
  id: 'first-account',
  email: 'first@example.com',
  displayName: 'First Account',
);
const _secondAccount = UserProfile(
  id: 'second-account',
  email: 'second@example.com',
  displayName: 'Second Account',
);

class _DelayedAnalysisRepository extends FakeRepository {
  _DelayedAnalysisRepository() : super(restoredUser: _firstAccount);

  Future<AnalysisResult>? nextLatest;
  Future<AnalysisResult>? nextRun;
  late AnalysisResult currentAnalysis = resultFor('first-cached');

  AnalysisResult resultFor(String id) => AnalysisResult(
    id: id,
    generatedAt: analysis.generatedAt,
    forecast: analysis.forecast,
    alerts: analysis.alerts,
    recommendations: analysis.recommendations,
  );

  @override
  Future<UserProfile> login(String email, String password) async =>
      _secondAccount;

  @override
  Future<AnalysisResult> latestAnalysis() {
    final pending = nextLatest;
    nextLatest = null;
    return pending ?? Future.value(currentAnalysis);
  }

  @override
  Future<AnalysisResult> runAnalysis({DateTime? historyCompleteFrom}) {
    final pending = nextRun;
    nextRun = null;
    return pending ?? Future.value(currentAnalysis);
  }
}

class _AnalysisProbe extends ConsumerWidget {
  const _AnalysisProbe();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);
    final analysis = ref.watch(analysisControllerProvider);
    return Text(
      '${auth.user?.id ?? 'signed-out'}: '
      '${analysis.result?.id ?? 'no-analysis'}: '
      '${analysis.error ?? 'no-error'}',
    );
  }
}

void main() {
  for (final operation in ['loadLatest', 'run']) {
    for (final outcome in ['success', 'offline', 'late-error']) {
      testWidgets(
        '$operation cannot republish previous account state after switching ($outcome)',
        (tester) async {
          final repository = _DelayedAnalysisRepository();
          await tester.pumpWidget(
            ProviderScope(
              overrides: [
                repositoryProvider.overrideWithValue(repository),
                googleIdentityProvider.overrideWithValue(FakeGoogleIdentity()),
              ],
              child: const MaterialApp(home: Scaffold(body: _AnalysisProbe())),
            ),
          );
          await tester.pumpAndSettle();

          final container = ProviderScope.containerOf(
            tester.element(find.byType(_AnalysisProbe)),
          );
          final auth = container.read(authControllerProvider.notifier);
          expect(
            container.read(authControllerProvider).user?.id,
            _firstAccount.id,
          );
          final firstController = container.read(
            analysisControllerProvider.notifier,
          );
          firstController.historyCompleteFrom = DateTime(2026, 1, 1);
          await firstController.loadLatest();
          await tester.pump();
          expect(find.textContaining('first-cached'), findsOneWidget);

          final delayed = Completer<AnalysisResult>();
          if (operation == 'loadLatest') {
            repository.nextLatest = delayed.future;
          } else {
            repository.nextRun = delayed.future;
          }
          final oldRequest = operation == 'loadLatest'
              ? firstController.loadLatest()
              : firstController.run();
          await tester.pump();
          expect(container.read(analysisControllerProvider).loading, isTrue);

          await auth.logout();
          await tester.pumpAndSettle();
          expect(container.read(authControllerProvider).user, isNull);
          expect(container.read(analysisControllerProvider).result, isNull);
          expect(container.read(analysisControllerProvider).error, isNull);
          expect(container.read(analysisControllerProvider).loading, isFalse);
          expect(find.textContaining('first-cached'), findsNothing);

          expect(
            await auth.login(_secondAccount.email, 'test-password'),
            isTrue,
          );
          await tester.pumpAndSettle();
          expect(
            container.read(authControllerProvider).user?.id,
            _secondAccount.id,
          );
          final secondController = container.read(
            analysisControllerProvider.notifier,
          );
          expect(secondController.historyCompleteFrom, isNull);
          expect(container.read(analysisControllerProvider).result, isNull);

          final published = <AnalysisState>[];
          final subscription = container.listen<AnalysisState>(
            analysisControllerProvider,
            (_, next) => published.add(next),
            fireImmediately: true,
          );
          addTearDown(subscription.close);

          repository.currentAnalysis = repository.resultFor('second-current');
          if (outcome == 'offline') {
            final failedRefresh = Completer<AnalysisResult>();
            repository.nextLatest = failedRefresh.future;
            final refresh = secondController.loadLatest();
            failedRefresh.completeError(
              Exception('Second account is offline.'),
            );
            await refresh;
          } else {
            await secondController.loadLatest();
          }
          await tester.pumpAndSettle();

          if (outcome == 'late-error') {
            delayed.completeError(Exception('First account request failed.'));
          } else {
            delayed.complete(repository.resultFor('first-delayed'));
          }
          await oldRequest;
          await tester.pumpAndSettle();

          final state = container.read(analysisControllerProvider);
          expect(state.loading, isFalse);
          if (outcome == 'offline') {
            expect(state.result, isNull);
            expect(state.error, contains('Second account is offline.'));
            expect(
              find.textContaining('Second account is offline.'),
              findsOneWidget,
            );
          } else {
            expect(state.result?.id, 'second-current');
            expect(state.error, isNull);
            expect(find.textContaining('second-current'), findsOneWidget);
          }
          expect(
            published.where(
              (state) => state.result?.id.startsWith('first-') ?? false,
            ),
            isEmpty,
          );
          expect(
            published.where(
              (state) => state.error?.contains('First account') ?? false,
            ),
            isEmpty,
          );
          expect(find.textContaining('first-cached'), findsNothing);
          expect(find.textContaining('first-delayed'), findsNothing);
          expect(tester.takeException(), isNull);
        },
      );
    }
  }
}
