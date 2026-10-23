import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../controllers/mpesa_controller.dart';
import '../widgets/common.dart';

const smsDisclosure =
    'Spendly will access M-PESA confirmation SMS on this device only after '
    'you accept and grant SMS permission. It filters M-PESA senders and parses financial '
    'confirmations locally. Unrelated conversations, OTPs and raw SMS bodies are not '
    'uploaded or saved by the importer. Normalized references, times, amounts, fees, '
    'categories and counterparties are synchronized to your Spendly account and may '
    'be viewed by authorized support administrators. Minimal normalized pending records '
    'and the credentials needed for background sync are encrypted on this device. '
    'Import is optional and separate from model-training permission. Turning it off '
    'or signing out stops access and clears pending imports; previously imported '
    'transactions remain in your account. Source identities and original normalized '
    'audit details are retained for deduplication and reversal checks. '
    'This tracks wallet inflows and outflows: transfers, deposits and cash withdrawals '
    'may need review and do not prove earnings or consumption. SMS matching is not '
    'verification by Safaricom. You can keep using manual entry and CSV import.';

class MpesaSettingsScreen extends ConsumerStatefulWidget {
  const MpesaSettingsScreen({super.key});
  @override
  ConsumerState<MpesaSettingsScreen> createState() =>
      _MpesaSettingsScreenState();
}

class _MpesaSettingsScreenState extends ConsumerState<MpesaSettingsScreen>
    with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (mounted &&
        state == AppLifecycleState.resumed &&
        !ref.read(mpesaControllerProvider).busy) {
      ref.read(mpesaControllerProvider.notifier).refresh();
    }
  }

  Future<void> _enable() async {
    final accepted = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        scrollable: true,
        title: const Text('Allow optional M-PESA import?'),
        content: const Text(smsDisclosure),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Keep off'),
          ),
          FilledButton(
            key: const Key('sms-accept-disclosure'),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Accept and enable'),
          ),
        ],
      ),
    );
    if (!mounted || accepted != true) return;
    await ref
        .read(mpesaControllerProvider.notifier)
        .enable(disclosureAccepted: true);
    if (!mounted || !ref.read(mpesaControllerProvider).status.active) return;
    await _history(firstEnable: true);
  }

  Future<void> _history({bool firstEnable = false}) async {
    final days = await showModalBottomSheet<int>(
      context: context,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Import existing M-PESA transactions?',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 12),
                const Text(
                  'Choose the messages Spendly may read. This scans only M-PESA senders; it does not reopen unrelated conversations.',
                ),
                if (firstEnable)
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Only new messages'),
                  ),
                for (final entry in const {
                  30: 'Last 30 days',
                  90: 'Last 90 days',
                  0: 'All available M-PESA confirmations',
                }.entries)
                  ListTile(
                    title: Text(entry.value),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.pop(context, entry.key),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
    if (mounted && days != null) {
      await ref.read(mpesaControllerProvider.notifier).sync(historyDays: days);
    }
  }

  @override
  Widget build(BuildContext context) {
    final view = ref.watch(mpesaControllerProvider);
    final status = view.status;
    final active = status.active;
    final title = !status.enabled
        ? 'Off'
        : !status.permission
        ? 'Permission required'
        : active
        ? 'Active'
        : 'Paused';
    return Scaffold(
      appBar: AppBar(title: const Text('Automatic M-PESA transactions')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            title,
            key: const Key('sms-import-status'),
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 12),
          const Text(
            'Automatically add confirmed M-PESA income and spending from this device. Spendly will not access SMS unless you enable this feature and grant permission.',
          ),
          const SizedBox(height: 16),
          if (!status.available && !view.busy)
            const SoftPanel(
              child: Text(
                'SMS capability is excluded from this build. Manual entry and CSV import remain available.',
              ),
            ),
          if (status.available && view.consent?.available == false)
            const SoftPanel(
              child: Text(
                'This service has not enabled SMS import. No SMS permission is requested.',
              ),
            ),
          if (view.busy) const LinearProgressIndicator(),
          const SizedBox(height: 12),
          if (!status.enabled)
            FilledButton(
              key: const Key('sms-enable'),
              onPressed:
                  view.busy ||
                      !status.available ||
                      status.error != null ||
                      view.consent?.available != true
                  ? null
                  : _enable,
              child: const Text('Enable optional SMS import'),
            ),
          if (status.enabled && !status.active)
            FilledButton(
              onPressed: view.busy ? null : _enable,
              child: const Text('Review disclosure and grant permission'),
            ),
          if (status.enabled || status.error != null)
            OutlinedButton(
              key: const Key('sms-disable'),
              onPressed: () =>
                  ref.read(mpesaControllerProvider.notifier).turnOff(),
              child: Text(
                status.enabled
                    ? 'Turn off automatic import'
                    : 'Clear local import data',
              ),
            ),
          if (active) ...[
            FilledButton.icon(
              key: const Key('sms-sync'),
              onPressed: view.busy
                  ? null
                  : () => ref.read(mpesaControllerProvider.notifier).sync(),
              icon: const Icon(Icons.sync),
              label: const Text('Sync now'),
            ),
            OutlinedButton(
              onPressed: view.busy ? null : _history,
              child: const Text('Import existing M-PESA transactions'),
            ),
          ],
          Text('Pending normalized records: ${status.pending}'),
          if (status.historyPending)
            const Text(
              'More selected history remains. Sync again or allow background import to continue.',
            ),
          Text(
            status.lastSync == null
                ? 'No successful sync yet'
                : 'Last successful sync: ${DateFormat.yMMMd().add_Hm().format(status.lastSync!)}',
          ),
          if (status.summary.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              'Last import summary',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            for (final entry in const {
              'checked': 'M-PESA sender messages checked',
              'valid': 'Valid confirmations',
              'created': 'Transactions created (including fees)',
              'duplicate': 'Duplicates skipped',
              'unsupported': 'Unsupported messages ignored',
              'invalid': 'Failed or invalid entries',
              'needs_review': 'Source or financial conflicts needing review',
              'reversals': 'Reversal events',
            }.entries)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  '${entry.value}: ${status.summary[entry.key] ?? 0}',
                ),
              ),
          ],
          if (view.message != null || status.error != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Text(
                view.message ?? status.error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          TextButton(
            onPressed: view.busy
                ? null
                : () => ref.read(mpesaControllerProvider.notifier).refresh(),
            child: const Text('Refresh settings'),
          ),
          const ExpansionTile(
            title: Text('How your SMS data is handled'),
            children: [
              Padding(padding: EdgeInsets.all(16), child: Text(smsDisclosure)),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            'Android may delay background jobs. Force-stop, revoked permissions or an expired session pause automatic import. Reopen Spendly to check its status. No automatic model training or per-message analysis is run.',
          ),
        ],
      ),
    );
  }
}
