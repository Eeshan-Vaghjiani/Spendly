import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_theme.dart';
import '../../data/models/models.dart';
import '../controllers/providers.dart';
import '../widgets/common.dart';
import 'transaction_entry_screen.dart';

class AlertScreen extends ConsumerStatefulWidget {
  const AlertScreen({super.key, required this.alerts});
  final List<AlertResult> alerts;
  @override
  ConsumerState<AlertScreen> createState() => _AlertScreenState();
}

class _AlertScreenState extends ConsumerState<AlertScreen> {
  String _explanation(AlertResult alert) {
    final text = alert.explanation?.trim() ?? '';
    if (text.isEmpty ||
        text.toLowerCase().contains('heuristic') ||
        text.toLowerCase().contains('threshold') ||
        text.contains('=')) {
      return 'This entry is different from what you usually record.';
    }
    return text;
  }

  late List<AlertResult> _alerts;
  final Set<String> _busy = {};
  String? _error;
  @override
  void initState() {
    super.initState();
    _alerts = List.of(widget.alerts);
  }

  Future<void> _open(AlertResult alert) async {
    final id = alert.transactionId;
    if (id == null || _busy.contains(id)) return;
    setState(() {
      _busy.add(id);
      _error = null;
    });
    final session = ref.read(authControllerProvider).user?.id;
    try {
      final transaction = await ref.read(repositoryProvider).transaction(id);
      if (!mounted || ref.read(authControllerProvider).user?.id != session) {
        return;
      }
      final changed = await Navigator.of(context).push<bool>(
        MaterialPageRoute(
          builder: (_) => TransactionEntryScreen(transaction: transaction),
        ),
      );
      if (!mounted || ref.read(authControllerProvider).user?.id != session) {
        return;
      }
      if (changed == true) {
        await ref.read(analysisControllerProvider.notifier).run();
        if (!mounted) return;
        final state = ref.read(analysisControllerProvider);
        setState(() {
          if (state.result != null && state.error == null) {
            _alerts = List.of(state.result!.alerts);
          }
          _error = state.error;
        });
      }
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy.remove(id));
    }
  }

  Future<void> _confirm(AlertResult alert) async {
    final id = alert.id;
    if (id == null || _busy.contains(id)) return;
    setState(() {
      _busy.add(id);
      _error = null;
    });
    final session = ref.read(authControllerProvider).user?.id;
    try {
      final updated = await ref
          .read(repositoryProvider)
          .reviewAlert(
            id,
            intentional: alert.reviewStatus != 'intentional',
            transactionReviewVersion: alert.transactionReviewVersion ?? '',
          );
      if (!mounted || ref.read(authControllerProvider).user?.id != session) {
        return;
      }
      setState(
        () => _alerts = _alerts.map((a) => a.id == id ? updated : a).toList(),
      );
      await ref.read(analysisControllerProvider.notifier).loadLatest();
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy.remove(id));
    }
  }

  @override
  Widget build(BuildContext context) {
    final alerts = _alerts.where((a) => a.isUnusualSpending).toList();
    final money = NumberFormat.currency(symbol: 'KES ', decimalDigits: 2);
    return Scaffold(
      appBar: AppBar(title: const Text('Spending check')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          if (alerts.isEmpty)
            const SoftPanel(
              child: Column(
                children: [
                  Icon(Icons.check_rounded, color: AppColors.primary, size: 42),
                  Text('Everything looks usual'),
                  Text(
                    'The latest check did not find a spending entry that needs your attention.',
                  ),
                ],
              ),
            )
          else ...[
            const SoftPanel(
              child: Text(
                'These are spending review prompts, not fraud findings. Check the entry, correct a mistake, or explicitly confirm that it was intentional.',
              ),
            ),
            const SizedBox(height: 16),
            for (final alert in alerts)
              Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: SoftPanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      StatusPill(
                        label: alert.reviewStatus == 'intentional'
                            ? 'Confirmed intentional'
                            : 'Review spending',
                        color: AppColors.primary,
                        icon: Icons.fact_check_outlined,
                      ),
                      const SizedBox(height: 12),
                      if (alert.transaction != null) ...[
                        Text(
                          '${money.format(alert.transaction!.amount)} · ${alert.transaction!.category.replaceAll('_', ' ')}',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        Text(
                          '${DateFormat.yMMMd().format(alert.transaction!.timestamp.toLocal())} · ${alert.transaction!.merchant ?? 'No merchant recorded'}',
                        ),
                        const SizedBox(height: 8),
                      ],
                      Text(_explanation(alert)),
                      if (alert.reviewStatus == 'intentional')
                        const Padding(
                          padding: EdgeInsets.only(top: 8),
                          child: Text(
                            'This expense stays in your totals. Refresh insights for updated budget advice.',
                          ),
                        ),
                      if (alert.reviewStatus == 'changed_since_review')
                        const Text(
                          'The transaction changed after your last review. Check the updated details.',
                        ),
                      const SizedBox(height: 12),
                      if (alert.transactionId != null &&
                          alert.reviewStatus != 'transaction_deleted')
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            OutlinedButton.icon(
                              key: ValueKey('open-alert-${alert.id}'),
                              onPressed: _busy.isNotEmpty
                                  ? null
                                  : () => _open(alert),
                              icon: const Icon(Icons.receipt_long),
                              label: const Text('Open transaction'),
                            ),
                            if (alert.id != null)
                              FilledButton(
                                key: ValueKey('confirm-alert-${alert.id}'),
                                onPressed: _busy.isNotEmpty
                                    ? null
                                    : () => _confirm(alert),
                                child: Text(
                                  alert.reviewStatus == 'intentional'
                                      ? 'Mark for review again'
                                      : 'This spending was intentional',
                                ),
                              ),
                          ],
                        )
                      else
                        const Text(
                          'The linked transaction is unavailable. Refresh insights to update this check.',
                        ),
                    ],
                  ),
                ),
              ),
          ],
        ],
      ),
    );
  }
}
