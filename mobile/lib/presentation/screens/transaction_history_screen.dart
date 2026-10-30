import '../../core/reporting_time.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../core/theme/app_theme.dart';
import '../../data/models/models.dart';
import '../controllers/providers.dart';
import '../widgets/common.dart';
import '../widgets/transaction_source_icon.dart';
import 'mpesa_settings_screen.dart';
import 'transaction_entry_screen.dart';
import 'transaction_upload_screen.dart';

class TransactionHistoryScreen extends ConsumerStatefulWidget {
  const TransactionHistoryScreen({super.key, this.onOpenMenu});

  final VoidCallback? onOpenMenu;

  @override
  ConsumerState<TransactionHistoryScreen> createState() =>
      _TransactionHistoryScreenState();
}

class _TransactionHistoryScreenState
    extends ConsumerState<TransactionHistoryScreen> {
  late Future<List<TransactionRecord>> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _future = ref.read(repositoryProvider).transactions();
    // A socket failure can arrive before FutureBuilder's next frame subscribes.
    // Keep the original future so the builder still displays its error/retry UI.
    _future.ignore();
  }

  Future<void> _openEntry([TransactionRecord? transaction]) async {
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => TransactionEntryScreen(transaction: transaction),
      ),
    );
    if (mounted) setState(_reload);
  }

  Future<void> _delete(String id) async {
    try {
      await ref.read(repositoryProvider).deleteTransaction(id);
      if (mounted) setState(_reload);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not delete transaction: $error')),
      );
      setState(_reload);
    }
  }

  @override
  Widget build(BuildContext context) {
    final money = NumberFormat.currency(symbol: 'KES ', decimalDigits: 2);
    return Scaffold(
      appBar: AppBar(
        leading: widget.onOpenMenu == null
            ? null
            : IconButton(
                key: const Key('open-quick-access'),
                tooltip: 'Open quick access menu',
                onPressed: widget.onOpenMenu,
                icon: const Icon(Icons.menu_rounded),
              ),
        title: const Text('Transactions'),
        actions: [
          IconButton(
            key: const Key('open-mpesa-sync'),
            tooltip: 'M-PESA sync',
            onPressed: () async {
              await Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => const MpesaSettingsScreen(),
                ),
              );
              if (mounted) setState(_reload);
            },
            icon: const Icon(Icons.sms_outlined),
          ),
          IconButton(
            tooltip: 'Upload CSV',
            onPressed: () async {
              await Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => const TransactionUploadScreen(),
                ),
              );
              if (mounted) setState(_reload);
            },
            icon: const Icon(Icons.upload_file),
          ),
          IconButton(
            tooltip: 'Refresh transactions',
            onPressed: () => setState(_reload),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openEntry(),
        icon: const Icon(Icons.add),
        label: const Text('Add transaction'),
      ),
      body: FutureBuilder<List<TransactionRecord>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return ErrorPanel(
              message: snapshot.error.toString(),
              onRetry: () => setState(_reload),
            );
          }
          final transactions = snapshot.data ?? const <TransactionRecord>[];
          if (transactions.isEmpty) {
            return const EmptyPanel(
              icon: Icons.receipt_long_outlined,
              message: 'No transactions yet. Add one manually or upload a CSV.',
            );
          }
          return RefreshIndicator(
            onRefresh: () async => setState(_reload),
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 96),
              itemCount: transactions.length,
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final transaction = transactions[index];
                final isExpense = transaction.transactionType == 'expense';
                return Dismissible(
                  key: ValueKey(transaction.id),
                  direction: DismissDirection.endToStart,
                  confirmDismiss: (_) => showDialog<bool>(
                    context: context,
                    builder: (context) => AlertDialog(
                      title: const Text('Delete transaction?'),
                      content: const Text('This action cannot be undone.'),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(context, false),
                          child: const Text('Cancel'),
                        ),
                        FilledButton(
                          onPressed: () => Navigator.pop(context, true),
                          child: const Text('Delete'),
                        ),
                      ],
                    ),
                  ),
                  onDismissed: (_) => _delete(transaction.id),
                  background: Container(
                    color: Theme.of(context).colorScheme.errorContainer,
                    alignment: Alignment.centerRight,
                    padding: const EdgeInsets.only(right: 24),
                    child: const Icon(Icons.delete_outline),
                  ),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor:
                          (isExpense ? AppColors.expense : AppColors.income)
                              .withValues(alpha: 0.12),
                      child: Icon(
                        isExpense
                            ? Icons.arrow_downward_rounded
                            : Icons.arrow_upward_rounded,
                        color: isExpense ? AppColors.expense : AppColors.income,
                      ),
                    ),
                    title: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(transaction.category.replaceAll('_', ' ')),
                        const SizedBox(height: 4),
                        Text(
                          '${isExpense ? '-' : '+'}${money.format(transaction.amount)}',
                          style: TextStyle(
                            color: isExpense
                                ? AppColors.expense
                                : AppColors.income,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(transaction.merchant ?? 'No merchant'),
                        Wrap(
                          crossAxisAlignment: WrapCrossAlignment.center,
                          children: [
                            Text(
                              DateFormat.yMMMd().format(
                                nairobiWallTime(transaction.timestamp),
                              ),
                            ),
                            TransactionSourceIcon(source: transaction.source),
                          ],
                        ),
                        if (transaction.isReversed)
                          const Text('Reversed — excluded from totals'),
                      ],
                    ),
                    onTap: () => _openEntry(transaction),
                    trailing: PopupMenuButton<String>(
                      tooltip: 'Transaction actions',
                      onSelected: (action) async {
                        if (action == 'edit') {
                          await _openEntry(transaction);
                        } else if (action == 'delete' && context.mounted) {
                          final confirmed = await showDialog<bool>(
                            context: context,
                            builder: (dialogContext) => AlertDialog(
                              title: const Text('Delete transaction?'),
                              content: const Text(
                                'This transaction will be permanently removed.',
                              ),
                              actions: [
                                TextButton(
                                  onPressed: () =>
                                      Navigator.pop(dialogContext, false),
                                  child: const Text('Cancel'),
                                ),
                                FilledButton(
                                  onPressed: () =>
                                      Navigator.pop(dialogContext, true),
                                  child: const Text('Delete'),
                                ),
                              ],
                            ),
                          );
                          if (confirmed == true) {
                            await _delete(transaction.id);
                          }
                        }
                      },
                      itemBuilder: (_) => const [
                        PopupMenuItem(
                          value: 'edit',
                          child: ListTile(
                            leading: Icon(Icons.edit_outlined),
                            title: Text('Edit'),
                            contentPadding: EdgeInsets.zero,
                          ),
                        ),
                        PopupMenuItem(
                          value: 'delete',
                          child: ListTile(
                            leading: Icon(Icons.delete_outline),
                            title: Text('Delete'),
                            contentPadding: EdgeInsets.zero,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
