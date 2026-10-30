import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../controllers/providers.dart';
import '../widgets/common.dart';

class AnalysisHistoryScreen extends ConsumerStatefulWidget {
  const AnalysisHistoryScreen({super.key});

  @override
  ConsumerState<AnalysisHistoryScreen> createState() =>
      _AnalysisHistoryScreenState();
}

class _AnalysisHistoryScreenState extends ConsumerState<AnalysisHistoryScreen> {
  late Map<String, Future<List<Map<String, dynamic>>> Function()> _loaders;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final repository = ref.read(repositoryProvider);
    _loaders = {
      'forecasts': () => repository.history('forecasts'),
      'alerts': () => repository.history('alerts'),
      'recommendations': () => repository.history('recommendations'),
    };
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Analysis history'),
          bottom: const TabBar(
            tabs: [
              Tab(text: 'Forecasts'),
              Tab(text: 'Alerts'),
              Tab(text: 'Advice'),
            ],
          ),
        ),
        body: TabBarView(
          children: [
            _HistoryList(
              load: _loaders['forecasts']!,
              resource: 'forecasts',
              onRetry: () => setState(_load),
            ),
            _HistoryList(
              load: _loaders['alerts']!,
              resource: 'alerts',
              onRetry: () => setState(_load),
            ),
            _HistoryList(
              load: _loaders['recommendations']!,
              resource: 'recommendations',
              onRetry: () => setState(_load),
            ),
          ],
        ),
      ),
    );
  }
}

class _HistoryList extends StatefulWidget {
  const _HistoryList({
    required this.load,
    required this.resource,
    required this.onRetry,
  });

  final Future<List<Map<String, dynamic>>> Function() load;
  final String resource;
  final VoidCallback onRetry;

  @override
  State<_HistoryList> createState() => _HistoryListState();
}

class _HistoryListState extends State<_HistoryList> {
  late Future<List<Map<String, dynamic>>> _future;

  String get resource => widget.resource;

  @override
  void initState() {
    super.initState();
    _future = widget.load();
  }

  @override
  void didUpdateWidget(covariant _HistoryList oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.load != oldWidget.load) _future = widget.load();
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<Map<String, dynamic>>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return ErrorPanel(
            message: snapshot.error.toString(),
            onRetry: widget.onRetry,
          );
        }
        final items = snapshot.data ?? const [];
        if (items.isEmpty) {
          return EmptyPanel(
            icon: Icons.history,
            message: 'No stored $resource are available.',
          );
        }
        return RefreshIndicator(
          onRefresh: () async => widget.onRetry(),
          child: ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: items.length,
            itemBuilder: (context, index) => _card(items[index]),
          ),
        );
      },
    );
  }

  Widget _card(Map<String, dynamic> item) {
    if (resource == 'forecasts') {
      final actual = (item['actual_spending'] as num?)?.toDouble();
      final predicted = (item['predicted_spending'] as num).toDouble();
      final accuracyText = actual == null
          ? 'Actual spending pending'
          : 'Difference from recorded spending: KES ${(predicted - actual).abs().toStringAsFixed(2)}';
      return Card(
        child: ListTile(
          leading: const Icon(Icons.insights_outlined),
          title: Text(
            NumberFormat.currency(
              symbol: '${item['currency'] ?? 'KES'} ',
              decimalDigits: 0,
            ).format(item['predicted_spending']),
          ),
          subtitle: Text(
            '${item['period_start']} – ${item['period_end']}\n'
            '${item['data_readiness_percent'] ?? 0}% data readiness · '
            'week ${item['history_weeks'] ?? 0}/8\n'
            '$accuracyText',
          ),
          isThreeLine: true,
        ),
      );
    }
    if (resource == 'alerts') {
      final unusual = item['is_unusual_spending'] == true;
      return Card(
        child: ListTile(
          leading: Icon(
            unusual ? Icons.warning_amber_rounded : Icons.check_circle_outline,
          ),
          title: Text(
            unusual ? 'Item worth checking' : 'Everything looked usual',
          ),
          subtitle: Text(
            unusual
                ? _friendlyAlertText('${item['explanation']}')
                : 'No action was needed for this check.',
          ),
        ),
      );
    }
    return Card(
      child: ListTile(
        leading: const Icon(Icons.tips_and_updates_outlined),
        title: Text('${item['title']}'),
        subtitle: Text('Try this: ${item['suggested_action']}'),
      ),
    );
  }

  String _friendlyAlertText(String text) {
    final lower = text.toLowerCase();
    if (lower.contains('heuristic') ||
        lower.contains('threshold') ||
        text.contains('=')) {
      return 'This entry was different from the user\'s usual spending pattern.';
    }
    return text;
  }
}
