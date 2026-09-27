import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/models.dart';
import '../controllers/providers.dart';

class TransactionEntryScreen extends ConsumerStatefulWidget {
  const TransactionEntryScreen({super.key, this.transaction});

  final TransactionRecord? transaction;

  @override
  ConsumerState<TransactionEntryScreen> createState() =>
      _TransactionEntryScreenState();
}

class _TransactionEntryScreenState
    extends ConsumerState<TransactionEntryScreen> {
  final _formKey = GlobalKey<FormState>();
  final _amount = TextEditingController();
  final _category = TextEditingController();
  final _merchant = TextEditingController();
  String _type = 'expense';
  bool _recurring = false;
  DateTime _timestamp = DateTime.now();
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final transaction = widget.transaction;
    if (transaction == null) return;
    _amount.text = transaction.amount.toStringAsFixed(2);
    _category.text = transaction.category.replaceAll('_', ' ');
    _merchant.text = transaction.merchant ?? '';
    _type = transaction.transactionType;
    _recurring = transaction.isRecurring;
    _timestamp = transaction.timestamp.toLocal();
  }

  @override
  void dispose() {
    _amount.dispose();
    _category.dispose();
    _merchant.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final repository = ref.read(repositoryProvider);
      final merchant = _merchant.text.trim().isEmpty
          ? null
          : _merchant.text.trim();
      if (widget.transaction == null) {
        await repository.addTransaction(
          timestamp: _timestamp,
          amount: double.parse(_amount.text),
          category: _category.text.trim(),
          transactionType: _type,
          merchant: merchant,
          isRecurring: _recurring,
        );
      } else {
        await repository.updateTransaction(
          id: widget.transaction!.id,
          timestamp: _timestamp,
          amount: double.parse(_amount.text),
          category: _category.text.trim(),
          transactionType: _type,
          merchant: merchant,
          isRecurring: _recurring,
        );
      }
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
        _saving = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.transaction == null ? 'Add transaction' : 'Edit transaction',
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'expense', label: Text('Expense')),
                    ButtonSegment(value: 'income', label: Text('Income')),
                  ],
                  selected: {_type},
                  onSelectionChanged: (value) =>
                      setState(() => _type = value.first),
                ),
                const SizedBox(height: 16),
                TextFormField(
                  key: const Key('transaction-amount'),
                  controller: _amount,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  decoration: const InputDecoration(
                    labelText: 'Amount (KES)',
                    prefixIcon: Icon(Icons.payments_outlined),
                  ),
                  validator: (value) {
                    final amount = double.tryParse(value ?? '');
                    return amount == null || amount <= 0
                        ? 'Enter an amount greater than zero.'
                        : null;
                  },
                ),
                const SizedBox(height: 16),
                TextFormField(
                  key: const Key('transaction-category'),
                  controller: _category,
                  decoration: const InputDecoration(
                    labelText: 'Category',
                    hintText: 'food, transport, salary…',
                  ),
                  validator: (value) => value == null || value.trim().isEmpty
                      ? 'Enter a category.'
                      : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _merchant,
                  decoration: const InputDecoration(
                    labelText: 'Merchant or source (optional)',
                  ),
                ),
                const SizedBox(height: 8),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Recurring transaction'),
                  value: _recurring,
                  onChanged: (value) => setState(() => _recurring = value),
                ),
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Transaction date'),
                  subtitle: Text(_timestamp.toLocal().toString()),
                  trailing: const Icon(Icons.calendar_today_outlined),
                  onTap: () async {
                    final selected = await showDatePicker(
                      context: context,
                      firstDate: DateTime(2020),
                      lastDate: DateTime.now().add(const Duration(days: 1)),
                      initialDate: _timestamp,
                    );
                    if (selected != null) {
                      setState(() => _timestamp = selected);
                    }
                  },
                ),
                if (_error != null)
                  Text(
                    _error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                const SizedBox(height: 16),
                FilledButton(
                  key: const Key('transaction-save'),
                  onPressed: _saving ? null : _save,
                  child: _saving
                      ? const CircularProgressIndicator()
                      : Text(
                          widget.transaction == null
                              ? 'Save transaction'
                              : 'Save changes',
                        ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
