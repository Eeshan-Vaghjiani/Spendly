import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../controllers/providers.dart';
import '../widgets/common.dart';
import '../widgets/privacy_summary.dart';

class ConsentSetupScreen extends ConsumerStatefulWidget {
  const ConsentSetupScreen({super.key})
    : email = null,
      password = null,
      displayName = null;

  const ConsentSetupScreen.registration({
    super.key,
    required this.email,
    required this.password,
    required this.displayName,
  });

  final String? email;
  final String? password;
  final String? displayName;

  bool get isRegistration => email != null;

  @override
  ConsumerState<ConsentSetupScreen> createState() => _ConsentSetupScreenState();
}

class _ConsentSetupScreenState extends ConsumerState<ConsentSetupScreen> {
  bool _serviceAccepted = false;
  bool _privacyAccepted = false;
  bool _trainingOptIn = false;

  Future<void> _continue() async {
    if (!_serviceAccepted || !_privacyAccepted) return;
    final controller = ref.read(authControllerProvider.notifier);
    final succeeded = widget.isRegistration
        ? await controller.register(
            widget.email!,
            widget.password!,
            widget.displayName!,
            acceptedTerms: true,
            acceptedPrivacy: true,
            modelTrainingOptIn: _trainingOptIn,
          )
        : await controller.updateConsent(modelTrainingOptIn: _trainingOptIn);
    if (succeeded && mounted && widget.isRegistration) {
      Navigator.of(context).popUntil((route) => route.isFirst);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    return PopScope(
      canPop: widget.isRegistration,
      child: Scaffold(
        appBar: AppBar(
          automaticallyImplyLeading: widget.isRegistration,
          title: const Text('Data and privacy setup'),
        ),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
          children: [
            Text(
              'Know what happens to your data',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 6),
            const Text(
              'Read this short summary before your account is activated.',
              style: TextStyle(color: AppColors.mutedInk),
            ),
            const SizedBox(height: 18),
            const PrivacySummary(),
            const SizedBox(height: 16),
            SoftPanel(
              child: Column(
                children: [
                  CheckboxListTile(
                    key: const Key('accept-service-terms'),
                    contentPadding: EdgeInsets.zero,
                    value: _serviceAccepted,
                    onChanged: (value) =>
                        setState(() => _serviceAccepted = value ?? false),
                    title: const Text('I accept the service terms'),
                    subtitle: const Text(
                      'Required to create and use the account.',
                    ),
                    controlAffinity: ListTileControlAffinity.leading,
                  ),
                  CheckboxListTile(
                    key: const Key('accept-privacy-use'),
                    contentPadding: EdgeInsets.zero,
                    value: _privacyAccepted,
                    onChanged: (value) =>
                        setState(() => _privacyAccepted = value ?? false),
                    title: const Text('I accept this data use'),
                    subtitle: const Text(
                      'Required for forecasts and spending insights.',
                    ),
                    controlAffinity: ListTileControlAffinity.leading,
                  ),
                  const Divider(),
                  SwitchListTile(
                    key: const Key('model-training-opt-in'),
                    contentPadding: EdgeInsets.zero,
                    value: _trainingOptIn,
                    onChanged: (value) =>
                        setState(() => _trainingOptIn = value),
                    title: const Text('Help improve future models'),
                    subtitle: const Text(
                      'Optional. The current app does not automatically train '
                      'on your records; this stores your choice for future '
                      'de-identified model improvement.',
                    ),
                  ),
                ],
              ),
            ),
            if (auth.error != null) ...[
              const SizedBox(height: 12),
              Text(
                auth.error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 18),
            FilledButton(
              key: const Key('complete-data-setup'),
              onPressed: auth.loading || !_serviceAccepted || !_privacyAccepted
                  ? null
                  : _continue,
              child: auth.loading
                  ? const SizedBox.square(
                      dimension: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : Text(
                      widget.isRegistration
                          ? 'Accept and create account'
                          : 'Accept and continue',
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
