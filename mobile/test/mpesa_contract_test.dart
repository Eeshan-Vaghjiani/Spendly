import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:spending_support/core/theme/app_theme.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/data/repositories/api_spending_repository.dart';
import 'package:spending_support/data/services/api_client.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/budget_screen.dart';
import 'api_client_test.dart' show MemoryTokenStore;
import 'widget_test.dart' show FakeRepository;

void main() {
  test(
    'SMS contracts send dedicated disclosure and normalized batches only',
    () async {
      final requests = <http.Request>[];
      final store = MemoryTokenStore()..token = 'synthetic-contract-token';
      final api = ApiClient(
        baseUrl: 'http://localhost/api/v1',
        tokenStore: store,
        httpClient: MockClient((request) async {
          requests.add(request);
          return http.Response(
            jsonEncode({
              'success': true,
              'data': {
                'account_id': 'alpha',
                'available': true,
                'enabled': request.method == 'PUT',
                'consent_version': '2026-10-22',
                'required_consent_version': '2026-10-22',
              },
            }),
            200,
          );
        }),
      );
      addTearDown(api.close);
      final repository = ApiSpendingRepository(api);
      expect((await repository.smsConsent()).accountId, 'alpha');
      await repository.updateSmsConsent(
        enabled: true,
        disclosureAccepted: true,
        version: '2026-10-22',
      );
      expect(jsonDecode(requests.last.body), {
        'enabled': true,
        'disclosure_accepted': true,
        'consent_version': '2026-10-22',
      });
      await repository.updateSmsConsent(enabled: false);
      expect(jsonDecode(requests.last.body), {'enabled': false});
      const normalized = {
        'external_reference': 'TEST000001',
        'amount': '120.00',
      };
      await repository.importMpesaEvents([normalized]);
      expect(requests.last.url.path, '/api/v1/transactions/mpesa/import');
      expect(jsonDecode(requests.last.body), {
        'events': [normalized],
      });
      expect(
        requests.every(
          (request) =>
              request.headers['Authorization'] ==
              'Bearer synthetic-contract-token',
        ),
        isTrue,
      );
    },
  );

  test(
    'SMS transaction metadata survives parsing and old responses remain readable',
    () {
      final legacy = {
        'id': 'fixture',
        'transaction_timestamp': '2026-10-22T10:00:00Z',
        'amount': 120,
        'category': 'transfers',
        'transaction_type': 'expense',
      };
      expect(TransactionRecord.fromJson(legacy).source, 'manual');
      expect(TransactionRecord.fromJson(legacy).isReversed, isFalse);
      final imported = TransactionRecord.fromJson({
        ...legacy,
        'source': 'mpesa_sms',
        'is_reversed': true,
      });
      expect(imported.source, 'mpesa_sms');
      expect(imported.isReversed, isTrue);
    },
  );

  testWidgets(
    'budget spending excludes reversed principal but retains non-refunded fee',
    (tester) async {
      final now = DateTime.now();
      final repository = FakeRepository();
      repository.createdBudgets.add(
        BudgetRecord(
          id: 'sms-budget',
          periodStart: now.subtract(const Duration(days: 1)),
          periodEnd: now.add(const Duration(days: 1)),
          category: 'total',
          amount: 100,
        ),
      );
      repository.createdTransactions.addAll([
        TransactionRecord(
          id: 'principal',
          timestamp: now,
          amount: 214.25,
          category: 'transfers',
          transactionType: 'expense',
          isRecurring: false,
          source: 'mpesa_sms',
          isReversed: true,
        ),
        TransactionRecord(
          id: 'fee',
          timestamp: now,
          amount: 8.50,
          category: 'transaction_fees',
          transactionType: 'expense',
          isRecurring: false,
          source: 'mpesa_sms',
        ),
      ]);
      await tester.pumpWidget(
        ProviderScope(
          overrides: [repositoryProvider.overrideWithValue(repository)],
          child: MaterialApp(
            theme: AppTheme.light(),
            home: const BudgetScreen(),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('9% used'), findsOneWidget);
      expect(find.textContaining('Over budget by'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );
}
