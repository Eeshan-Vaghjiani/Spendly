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
    return Scaffold(
      appBar: AppBar(title: const Text('Upload transactions')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'Choose a UTF-8 CSV using the documented template. Invalid '
                'rows and duplicates are reported and never silently discarded.',
              ),
            ),
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
          ],
        ],
      ),
    );
  }
}
