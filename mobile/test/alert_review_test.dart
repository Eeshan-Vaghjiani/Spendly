import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/alert_screen.dart';
import 'package:spending_support/presentation/screens/transaction_entry_screen.dart';

import 'widget_test.dart' show FakeGoogleIdentity, FakeRepository;

const _account = UserProfile(
  id: 'alert-review-user',
  email: 'alert-review@example.com',
  displayName: 'Alert Reviewer',
);

final _linkedTransaction = TransactionRecord(
  id: 'linked-transaction',
  timestamp: DateTime(2026, 7, 25, 12),
  amount: 4200,
  category: 'eating_out',
  transactionType: 'expense',
  merchant: 'Test Cafe',
  isRecurring: false,
);

AlertResult _alert({
  String? transactionId = 'linked-transaction',
  String reviewStatus = 'pending',
  String version = 'transaction-version-1',
}) => AlertResult(
  id: 'alert-1',
  isUnusualSpending: true,
  explanation: 'This meal cost more than your usual meals.',
  transactionId: transactionId,
  transaction: transactionId == null ? null : _linkedTransaction,
  reviewStatus: reviewStatus,
  transactionReviewVersion: version,
);

class _AlertRepository extends FakeRepository {
  _AlertRepository() : super(restoredUser: _account);

  final transactionRequests = <String>[];
  final reviews = <({String id, bool intentional, String expectedVersion})>[];
  Completer<AlertResult>? pendingReview;
  Object? reviewError;
  Object? transactionError;
  int latestAnalysisCalls = 0;

  @override
  Future<TransactionRecord> transaction(String id) async {
    transactionRequests.add(id);
    if (transactionError != null) throw transactionError!;
    return super.transaction(id);
  }

  @override
  Future<AlertResult> reviewAlert(
    String id, {
    required bool intentional,
    required String transactionReviewVersion,
  }) async {
    reviews.add((
      id: id,
      intentional: intentional,
      expectedVersion: transactionReviewVersion,
    ));
    if (reviewError != null) throw reviewError!;
    if (pendingReview != null) return pendingReview!.future;
    return _alert(reviewStatus: intentional ? 'intentional' : 'pending');
  }

  @override
  Future<AnalysisResult> latestAnalysis() async {
    latestAnalysisCalls += 1;
    return super.latestAnalysis();
  }
}

Future<void> _pumpAlert(
  WidgetTester tester,
  _AlertRepository repository, {
  AlertResult? alert,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        repositoryProvider.overrideWithValue(repository),
        googleIdentityProvider.overrideWithValue(FakeGoogleIdentity()),
      ],
      child: Consumer(
        builder: (context, ref, child) {
          // Finish session restoration before exercising session-guarded actions.
          ref.watch(authControllerProvider);
          return MaterialApp(home: AlertScreen(alerts: [alert ?? _alert()]));
        },
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('shows linked transaction details without reviewing it', (
    tester,
  ) async {
    final repository = _AlertRepository();
    await _pumpAlert(tester, repository);

    expect(find.text('KES 4,200.00 · eating out'), findsOneWidget);
    expect(find.text('Jul 25, 2026 · Test Cafe'), findsOneWidget);
    expect(
      find.text('This meal cost more than your usual meals.'),
      findsOneWidget,
    );
    expect(find.text('Open transaction'), findsOneWidget);
    expect(find.text('This spending was intentional'), findsOneWidget);
    expect(repository.reviews, isEmpty);
    expect(repository.transactionRequests, isEmpty);
  });

  testWidgets('explicit review sends expected version and supports undo', (
    tester,
  ) async {
    final repository = _AlertRepository();
    final response = Completer<AlertResult>();
    repository.pendingReview = response;
    await _pumpAlert(tester, repository);

    final confirm = find.byKey(const Key('confirm-alert-alert-1'));
    await tester.ensureVisible(confirm);
    await tester.tap(confirm);
    await tester.pump();

    expect(repository.reviews, [
      (
        id: 'alert-1',
        intentional: true,
        expectedVersion: 'transaction-version-1',
      ),
    ]);
    expect(find.text('Confirmed intentional'), findsNothing);
    expect(tester.widget<FilledButton>(confirm).onPressed, isNull);
    expect(
      tester
          .widget<OutlinedButton>(find.byKey(const Key('open-alert-alert-1')))
          .onPressed,
      isNull,
    );

    response.complete(
      _alert(reviewStatus: 'intentional', version: 'transaction-version-2'),
    );
    repository.pendingReview = null;
    await tester.pumpAndSettle();

    expect(find.text('Confirmed intentional'), findsOneWidget);
    expect(find.text('Mark for review again'), findsOneWidget);
    expect(
      find.textContaining('This expense stays in your totals.'),
      findsOneWidget,
    );
    expect(repository.latestAnalysisCalls, 1);

    await tester.ensureVisible(confirm);
    await tester.tap(confirm);
    await tester.pumpAndSettle();

    expect(repository.reviews, [
      (
        id: 'alert-1',
        intentional: true,
        expectedVersion: 'transaction-version-1',
      ),
      (
        id: 'alert-1',
        intentional: false,
        expectedVersion: 'transaction-version-2',
      ),
    ]);
    expect(find.text('Confirmed intentional'), findsNothing);
    expect(find.text('This spending was intentional'), findsOneWidget);
    expect(repository.latestAnalysisCalls, 2);
    expect(tester.takeException(), isNull);
  });

  testWidgets('open fetches current record into the real transaction editor', (
    tester,
  ) async {
    final repository = _AlertRepository();
    final current = TransactionRecord(
      id: _linkedTransaction.id,
      timestamp: DateTime(2026, 7, 26, 12),
      amount: 3900,
      category: 'food',
      transactionType: 'expense',
      merchant: 'Updated Test Cafe',
      isRecurring: true,
    );
    repository.createdTransactions.add(current);
    await _pumpAlert(tester, repository);

    final open = find.byKey(const Key('open-alert-alert-1'));
    await tester.ensureVisible(open);
    await tester.tap(open);
    await tester.pumpAndSettle();

    expect(repository.transactionRequests, ['linked-transaction']);
    expect(find.text('Edit transaction'), findsOneWidget);
    expect(
      tester
          .widget<TransactionEntryScreen>(find.byType(TransactionEntryScreen))
          .transaction,
      same(current),
    );
    expect(
      tester
          .widget<TextFormField>(find.byKey(const Key('transaction-amount')))
          .controller!
          .text,
      '3900.00',
    );
    expect(
      tester
          .widget<TextFormField>(find.byKey(const Key('transaction-category')))
          .controller!
          .text,
      'food',
    );
    expect(find.text('Updated Test Cafe'), findsOneWidget);
    expect(
      tester.widget<SwitchListTile>(find.byType(SwitchListTile)).value,
      isTrue,
    );
    expect(repository.reviews, isEmpty);
    expect(tester.takeException(), isNull);
  });

  for (final deleted in [false, true]) {
    testWidgets(
      '${deleted ? 'deleted' : 'missing'} transaction link is unavailable',
      (tester) async {
        final repository = _AlertRepository();
        await _pumpAlert(
          tester,
          repository,
          alert: _alert(
            transactionId: deleted ? 'linked-transaction' : null,
            reviewStatus: deleted ? 'transaction_deleted' : 'pending',
          ),
        );

        expect(
          find.text(
            'The linked transaction is unavailable. Refresh insights to update this check.',
          ),
          findsOneWidget,
        );
        expect(find.byKey(const Key('open-alert-alert-1')), findsNothing);
        expect(find.byKey(const Key('confirm-alert-alert-1')), findsNothing);
        expect(repository.transactionRequests, isEmpty);
        expect(repository.reviews, isEmpty);
      },
    );
  }

  testWidgets('failed review is visible and leaves review action available', (
    tester,
  ) async {
    final repository = _AlertRepository()
      ..reviewError = Exception('Review request failed. Try again.');
    await _pumpAlert(tester, repository);
    final confirm = find.byKey(const Key('confirm-alert-alert-1'));
    await tester.ensureVisible(confirm);
    await tester.tap(confirm);
    await tester.pumpAndSettle();

    expect(
      find.textContaining('Review request failed. Try again.'),
      findsOneWidget,
    );
    expect(find.text('Confirmed intentional'), findsNothing);
    expect(tester.widget<FilledButton>(confirm).onPressed, isNotNull);
    expect(repository.reviews, hasLength(1));
    expect(repository.latestAnalysisCalls, 0);
    expect(tester.takeException(), isNull);
  });

  testWidgets('failed transaction fetch is visible without opening editor', (
    tester,
  ) async {
    final repository = _AlertRepository()
      ..transactionError = Exception('Transaction could not be loaded.');
    await _pumpAlert(tester, repository);
    final open = find.byKey(const Key('open-alert-alert-1'));
    await tester.ensureVisible(open);
    await tester.tap(open);
    await tester.pumpAndSettle();

    expect(
      find.textContaining('Transaction could not be loaded.'),
      findsOneWidget,
    );
    expect(find.byType(TransactionEntryScreen), findsNothing);
    expect(tester.widget<OutlinedButton>(open).onPressed, isNotNull);
    expect(repository.transactionRequests, ['linked-transaction']);
    expect(repository.reviews, isEmpty);
    expect(tester.takeException(), isNull);
  });
}
