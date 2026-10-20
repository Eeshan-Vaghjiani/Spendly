import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/api_exception.dart';
import '../controllers/providers.dart';

class TransactionUploadScreen extends ConsumerStatefulWidget {
  const TransactionUploadScreen({super.key});

  @override
  ConsumerState<TransactionUploadScreen> createState() =>
      _TransactionUploadScreenState();
}

class _TransactionUploadScreenState
    extends ConsumerState<TransactionUploadScreen> {
  bool _loading = false;
  Map<String, dynamic>? _summary;
  String? _error;

  Future<void> _pickAndUpload() async {
    if (_loading) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final selection = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['csv'],
        withData: false,
      );
      if (!mounted || selection == null) return;
      final path = selection.files.single.path;
      if (path == null) {
        throw const ApiException(
          'FILE_UNAVAILABLE',
          'The selected file could not be read. Choose a CSV saved on this device.',
        );
      }
      setState(() => _summary = null);
      final summary = await ref
          .read(repositoryProvider)
          .uploadTransactions(path);
      if (!mounted) return;
      setState(() => _summary = summary);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error is ApiException
            ? error.message
            : 'The CSV file could not be selected or uploaded. Please try again.';
      });
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final errors = (_summary?['errors'] is List)
        ? (_summary!['errors'] as List).whereType<Map>().toList()
        : <Map>[];
    return Scaffold(
      appBar: AppBar(title: const Text('Upload transactions')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'Import your own transactions from a UTF-8 CSV. Valid rows '
                'are saved; duplicates are skipped and invalid rows are reported.',
              ),
            ),
          ),
          const ExpansionTile(
            key: Key('csv-format-help'),
            title: Text('CSV format and example'),
            expandedCrossAxisAlignment: CrossAxisAlignment.start,
            childrenPadding: EdgeInsets.fromLTRB(16, 0, 16, 16),
            children: [
              Text(
                'Use all six column names exactly as shown. Keep the merchant '
                'column even if its value is blank. Each transaction goes on '
                'a new row. The example below uses synthetic data.',
              ),
              SizedBox(height: 12),
              SelectableText(
                'transaction_timestamp,amount,category,transaction_type,merchant,is_recurring\n'
                '2026-10-19T12:30:00+03:00,125.50,food,expense,Synthetic shop,false',
                key: Key('csv-example'),
              ),
              SizedBox(height: 12),
              Text(
                'Date: ISO 8601, including the timezone (the example uses '
                'Nairobi +03:00). Amount: positive KES with at most two decimal '
                'places, without currency symbols or thousands separators. '
                'Type: expense or income. Recurring: true or false. '
                'Categories can include food, transport, utilities or salary. '
                'Save as CSV UTF-8, not an Excel workbook.',
              ),
            ],
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed: _loading ? null : _pickAndUpload,
            icon: const Icon(Icons.upload_file),
            label: const Text('Choose CSV file'),
          ),
          if (_loading) const LinearProgressIndicator(),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          if (_summary != null) ...[
            const SizedBox(height: 20),
            Text(
              'Upload summary',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            ListTile(
              title: const Text('Rows received'),
              trailing: Text('${_summary!['received_rows']}'),
            ),
            ListTile(
              title: const Text('Rows created'),
              trailing: Text('${_summary!['created_rows']}'),
            ),
            ListTile(
              title: const Text('Duplicates'),
              trailing: Text('${_summary!['duplicate_rows']}'),
            ),
            ListTile(
              title: const Text('Invalid rows'),
              trailing: Text('${_summary!['invalid_rows']}'),
            ),
            if (errors.isNotEmpty) ...[
              const Text(
                'Rejected rows',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
              const Text(
                'Row numbers include the header as row 1. Correct these rows '
                'and import again. Already saved identical transactions are '
                'skipped as duplicates.',
              ),
              for (final error in errors.take(20))
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(_rowError(error)),
                ),
              if (errors.length > 20)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    'Showing the first 20 of ${errors.length} rejected rows. '
                    'Fix these and import again to check the remaining rows.',
                  ),
                ),
            ] else if ((_summary!['invalid_rows'] as num? ?? 0) > 0)
              const Text(
                'Row details were not returned. Check the CSV format and '
                'invalid values before importing again.',
              ),
          ],
        ],
      ),
    );
  }

  String _rowError(Map error) {
    final row = error['row'];
    final raw = error['message'];
    final message = raw is String && raw.trim().isNotEmpty
        ? raw.trim()
        : 'Check the required columns and values.';
    final bounded = message.length > 500
        ? '${message.substring(0, 500)}…'
        : message;
    return 'Row ${row is int && row >= 2 ? row : 'unknown'}: $bounded';
  }
}
