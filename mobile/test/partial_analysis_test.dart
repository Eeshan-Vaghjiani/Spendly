import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/data/repositories/api_spending_repository.dart';
import 'package:spending_support/data/services/api_client.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/dashboard_screen.dart';
import 'api_client_test.dart' show MemoryTokenStore;
import 'widget_test.dart' show FakeRepository;

const message =
    'At least eight complete recorded weeks before this week are needed for the LSTM estimate.';
Map<String, dynamic> partialJson() => {
  'analysis_run_id': 'partial-1',
  'generated_at': '2026-10-19T12:00:00Z',
  'forecast': null,
  'forecast_unavailable': {'code': 'INSUFFICIENT_HISTORY', 'message': message},
  'alert_summary': {
    'alerts': [
      {'is_unusual_spending': true, 'explanation': 'Review this entry.'},
    ],
  },
  'recommendations': [
    {
      'recommendation_code': 'RECORD',
      'title': 'Keep recording spending',
      'message': 'Add entries.',
      'severity': 'low',
      'reason': 'Short history',
      'suggested_action': 'Record expenses.',
      'disclaimer': 'Decision support only.',
    },
  ],
};

class PartialRepository extends FakeRepository {
  bool offline = false;
  @override
  AnalysisResult get analysis => AnalysisResult.fromJson(partialJson());
  @override
  Future<AnalysisResult> runAnalysis({DateTime? historyCompleteFrom}) async {
    if (offline) throw Exception('Offline. Please try again.');
    return analysis;
  }
}

void main() {
  test('repository requests and restores partial results', () async {
    final requests = <http.Request>[];
    final repository = ApiSpendingRepository(
      ApiClient(
        baseUrl: 'http://localhost/api/v1',
        tokenStore: MemoryTokenStore(),
        httpClient: MockClient((request) async {
          requests.add(request);
          return http.Response(
            jsonEncode({'success': true, 'data': partialJson()}),
            200,
          );
        }),
      ),
    );
    final run = await repository.runAnalysis(
      historyCompleteFrom: DateTime(2026, 9, 1),
    );
    final latest = await repository.latestAnalysis();
    expect(jsonDecode(requests.first.body)['allow_partial_results'], true);
    expect(
      jsonDecode(requests.first.body)['history_complete_from'],
      '2026-09-01',
    );
    expect(requests.last.url.queryParameters['allow_partial_results'], 'true');
    expect(run.forecast, isNull);
    expect(latest.forecastUnavailableMessage, message);
    expect(latest.alerts.single.isUnusualSpending, true);
    expect(latest.recommendations.single.code, 'RECORD');
  });
  testWidgets('partial dashboard preserves insights and recovers offline', (
    tester,
  ) async {
    final repository = PartialRepository();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [repositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: DashboardScreen()),
      ),
    );
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.byKey(const Key('forecast-unavailable')),
      250,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Weekly estimate unavailable'), findsOneWidget);
    expect(find.text(message), findsOneWidget);
    expect(find.byKey(const Key('confirm-recorded-history')), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Spending check'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('1 item to review'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Keep recording spending'),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Keep recording spending'), findsOneWidget);
    final container = ProviderScope.containerOf(
      tester.element(find.byType(DashboardScreen)),
    );
    repository.offline = true;
    await container.read(analysisControllerProvider.notifier).run();
    await tester.pumpAndSettle();
    expect(container.read(analysisControllerProvider).result?.id, 'partial-1');
    await tester.scrollUntilVisible(
      find.textContaining('Could not refresh insights.'),
      -200,
      scrollable: find.byType(Scrollable).first,
    );
    expect(
      find.textContaining('Showing your last saved result.'),
      findsOneWidget,
    );
    repository.offline = false;
    await container.read(analysisControllerProvider.notifier).run();
    await tester.pumpAndSettle();
    expect(container.read(analysisControllerProvider).error, isNull);
    expect(tester.takeException(), isNull);
  });
}
