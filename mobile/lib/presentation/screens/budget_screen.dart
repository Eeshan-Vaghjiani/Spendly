import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../data/models/models.dart';
import '../../core/theme/app_theme.dart';
import '../controllers/providers.dart';
import '../widgets/common.dart';

class BudgetScreen extends ConsumerStatefulWidget {
  const BudgetScreen({super.key, this.onOpenMenu});

  final VoidCallback? onOpenMenu;

  @override
  ConsumerState<BudgetScreen> createState() => _BudgetScreenState();
}

class _BudgetScreenState extends ConsumerState<BudgetScreen> {
  late Future<_BudgetSnapshot> _future;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    final repository = ref.read(repositoryProvider);
    _future = Future.wait([repository.budgets(), repository.transactions()])
        .then(
          (values) => _BudgetSnapshot(
            budgets: values[0] as List<BudgetRecord>,
            transactions: values[1] as List<TransactionRecord>,
          ),
        );
  }

  Future<void> _openBudget([BudgetRecord? budget]) async {
    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => _BudgetDialog(
        budget: budget,
        onSave: (amount, category, periodStart, periodEnd) async {
          final repository = ref.read(repositoryProvider);
          if (budget == null) {
            await repository.createBudget(
              periodStart: periodStart,
              periodEnd: periodEnd,
              category: category,
              amount: amount,
            );
          } else {
            await repository.updateBudget(
              id: budget.id,
              periodStart: periodStart,
              periodEnd: periodEnd,
              category: category,
              amount: amount,
            );
          }
        },
      ),
    );
    if (saved == true && mounted) setState(_reload);
  }

  Future<void> _deleteBudget(BudgetRecord budget) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Delete budget?'),
        content: Text(
          'The ${budget.category.replaceAll('_', ' ')} budget will be permanently removed.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await ref.read(repositoryProvider).deleteBudget(budget.id);
      if (mounted) setState(_reload);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not delete budget: $error')),
      );
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
        title: const Text('Budgets'),
        actions: [
          IconButton(
            tooltip: 'Refresh budgets',
            onPressed: () => setState(_reload),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openBudget(),
        icon: const Icon(Icons.add),
        label: const Text('Add budget'),
      ),
      body: FutureBuilder<_BudgetSnapshot>(
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
          final budgetSnapshot = snapshot.requireData;
          final budgets = budgetSnapshot.budgets;
          if (budgets.isEmpty) {
            return const EmptyPanel(
              icon: Icons.savings_outlined,
              message: 'No budget is configured.',
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
            itemCount: budgets.length,
            separatorBuilder: (_, _) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final budget = budgets[index];
              return _BudgetCard(
                budget: budget,
                transactions: budgetSnapshot.transactions,
                money: money,
                onTap: () => _openBudget(budget),
                onEdit: () => _openBudget(budget),
                onDelete: () => _deleteBudget(budget),
              );
            },
          );
        },
      ),
    );
  }
}

class _BudgetSnapshot {
  const _BudgetSnapshot({required this.budgets, required this.transactions});

  final List<BudgetRecord> budgets;
  final List<TransactionRecord> transactions;
}

class _BudgetCard extends StatelessWidget {
  const _BudgetCard({
    required this.budget,
    required this.transactions,
    required this.money,
    required this.onTap,
    required this.onEdit,
    required this.onDelete,
  });

  final BudgetRecord budget;
  final List<TransactionRecord> transactions;
  final NumberFormat money;
  final VoidCallback onTap;
  final VoidCallback onEdit;
  final VoidCallback onDelete;

  DateTime _dateOnly(DateTime value) {
    final local = value.toLocal();
    return DateTime(local.year, local.month, local.day);
  }

  @override
  Widget build(BuildContext context) {
    final category = budget.category.trim().toLowerCase().replaceAll(' ', '_');
    final periodItems = transactions.where((item) {
      final date = _dateOnly(item.timestamp);
      return !date.isBefore(_dateOnly(budget.periodStart)) &&
          !date.isAfter(_dateOnly(budget.periodEnd));
    });
    final expenses = periodItems.where(
      (item) =>
          item.transactionType == 'expense' &&
          (category == 'total' || item.category.toLowerCase() == category),
    );
    final income = periodItems
        .where((item) => item.transactionType == 'income')
        .fold<double>(0, (sum, item) => sum + item.amount);
    final spent = expenses.fold<double>(0, (sum, item) => sum + item.amount);
    final budgetLeft = budget.amount - spent;
    final cashBalance = income - spent;
    final availableToSpend = income > 0
        ? mathMax(0, mathMin(cashBalance, budgetLeft))
        : mathMax(0, budgetLeft);
    final percentage = budget.amount > 0 ? spent / budget.amount * 100 : 0.0;
    final overBudget = percentage > 100;
    final nearingLimit = !overBudget && percentage >= 80;
    final accent = overBudget
        ? AppColors.expense
        : nearingLimit
        ? const Color(0xFF9A6200)
        : AppColors.primary;
    final surface = overBudget
        ? const Color(0xFFFFF1EF)
        : nearingLimit
        ? const Color(0xFFFFF8E8)
        : AppColors.surface;

    return Semantics(
      label:
          '${budget.category} budget, ${percentage.toStringAsFixed(0)} percent used',
      button: true,
      child: Material(
        color: surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(22),
          side: BorderSide(color: accent, width: overBudget ? 2 : 1),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 15, 10, 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      width: 42,
                      height: 42,
                      decoration: BoxDecoration(
                        color: accent.withValues(alpha: .13),
                        borderRadius: BorderRadius.circular(13),
                      ),
                      child: Icon(
                        overBudget
                            ? Icons.warning_amber_rounded
                            : Icons.savings_outlined,
                        color: accent,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            budget.category.replaceAll('_', ' '),
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${DateFormat.yMMMd().format(budget.periodStart)} – '
                            '${DateFormat.yMMMd().format(budget.periodEnd)}',
                            style: Theme.of(context).textTheme.bodySmall
                                ?.copyWith(color: AppColors.mutedInk),
                          ),
                        ],
                      ),
                    ),
                    PopupMenuButton<String>(
                      tooltip: 'Budget actions',
                      onSelected: (action) {
                        if (action == 'edit') onEdit();
                        if (action == 'delete') onDelete();
                      },
                      itemBuilder: (_) => const [
                        PopupMenuItem(value: 'edit', child: Text('Edit')),
                        PopupMenuItem(value: 'delete', child: Text('Delete')),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 15),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        '${percentage.toStringAsFixed(0)}% used',
                        style: TextStyle(
                          color: accent,
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                    Text(
                      '${money.format(spent)} of ${money.format(budget.amount)}',
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                ClipRRect(
                  borderRadius: BorderRadius.circular(99),
                  child: LinearProgressIndicator(
                    value: (percentage / 100).clamp(0, 1),
                    minHeight: 10,
                    color: accent,
                    backgroundColor: accent.withValues(alpha: .13),
                  ),
                ),
                if (overBudget) ...[
                  const SizedBox(height: 10),
                  StatusPill(
                    label:
                        'Over budget by ${money.format(spent - budget.amount)}',
                    color: AppColors.expense,
                    icon: Icons.error_outline,
                  ),
                ],
                const SizedBox(height: 15),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _MoneyFact(
                      label: 'Cash in',
                      value: money.format(income),
                      color: AppColors.income,
                    ),
                    _MoneyFact(
                      label: 'Actually spent',
                      value: money.format(spent),
                      color: AppColors.expense,
                    ),
                    _MoneyFact(
                      label: budgetLeft < 0 ? 'Budget exceeded' : 'Budget left',
                      value: money.format(budgetLeft.abs()),
                      color: budgetLeft < 0 ? AppColors.expense : accent,
                    ),
                    _MoneyFact(
                      label: cashBalance < 0 ? 'Cash shortfall' : 'Saved',
                      value: money.format(cashBalance.abs()),
                      color: cashBalance < 0
                          ? AppColors.expense
                          : AppColors.income,
                    ),
                    _MoneyFact(
                      label: 'Available to spend',
                      value: money.format(availableToSpend),
                      color: AppColors.primary,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

double mathMin(double left, double right) => left < right ? left : right;
double mathMax(double left, double right) => left > right ? left : right;

class _MoneyFact extends StatelessWidget {
  const _MoneyFact({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 126),
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .08),
        borderRadius: BorderRadius.circular(13),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.labelSmall?.copyWith(color: AppColors.mutedInk),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(color: color, fontWeight: FontWeight.w800),
          ),
        ],
      ),
    );
  }
}

class _BudgetDialog extends StatefulWidget {
  const _BudgetDialog({required this.onSave, this.budget});

  final BudgetRecord? budget;
  final Future<void> Function(
    double amount,
    String category,
    DateTime periodStart,
    DateTime periodEnd,
  )
  onSave;

  @override
  State<_BudgetDialog> createState() => _BudgetDialogState();
}

class _BudgetDialogState extends State<_BudgetDialog> {
  final _amount = TextEditingController();
  final _category = TextEditingController(text: 'total');
  late DateTime _periodStart;
  late DateTime _periodEnd;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final budget = widget.budget;
    final now = DateTime.now();
    _periodStart =
        budget?.periodStart ?? DateTime(now.year, now.month, now.day);
    _periodEnd = budget?.periodEnd ?? _periodStart.add(const Duration(days: 6));
    if (budget != null) {
      _amount.text = budget.amount.toStringAsFixed(2);
      _category.text = budget.category.replaceAll('_', ' ');
    }
  }

  @override
  void dispose() {
    _amount.dispose();
    _category.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    final amount = double.tryParse(_amount.text);
    final category = _category.text.trim();
    if (amount == null || amount <= 0 || category.isEmpty) {
      setState(() {
        _error = 'Enter an amount greater than zero and a category.';
      });
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await widget.onSave(amount, category, _periodStart, _periodEnd);
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = error.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(
        widget.budget == null ? 'Create weekly budget' : 'Edit weekly budget',
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              key: const Key('budget-amount'),
              controller: _amount,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              decoration: const InputDecoration(labelText: 'Amount (KES)'),
            ),
            const SizedBox(height: 8),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.date_range_outlined),
              title: const Text('Starts'),
              subtitle: Text(DateFormat.yMMMd().format(_periodStart)),
              onTap: () async {
                final date = await showDatePicker(
                  context: context,
                  initialDate: _periodStart,
                  firstDate: DateTime(2020),
                  lastDate: DateTime.now().add(const Duration(days: 730)),
                );
                if (date != null) {
                  setState(() {
                    _periodStart = date;
                    if (_periodEnd.isBefore(date)) {
                      _periodEnd = date.add(const Duration(days: 6));
                    }
                  });
                }
              },
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const Icon(Icons.event_available_outlined),
              title: const Text('Ends'),
              subtitle: Text(DateFormat.yMMMd().format(_periodEnd)),
              onTap: () async {
                final date = await showDatePicker(
                  context: context,
                  initialDate: _periodEnd,
                  firstDate: _periodStart,
                  lastDate: _periodStart.add(const Duration(days: 730)),
                );
                if (date != null) setState(() => _periodEnd = date);
              },
            ),
            const SizedBox(height: 12),
            TextField(
              key: const Key('budget-category'),
              controller: _category,
              decoration: const InputDecoration(labelText: 'Category'),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.pop(context, false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          key: const Key('budget-create'),
          onPressed: _saving ? null : _create,
          child: _saving
              ? const SizedBox.square(
                  dimension: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(widget.budget == null ? 'Create' : 'Save changes'),
        ),
      ],
    );
  }
}
