import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../controllers/providers.dart';
import '../widgets/common.dart';
import '../widgets/app_version_tile.dart';
import 'onboarding_screen.dart';
import 'privacy_info_screen.dart';
import 'mpesa_settings_screen.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  final _search = TextEditingController();

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  bool _matches(String text) =>
      text.toLowerCase().contains(_search.text.trim().toLowerCase());

  Future<void> _editUsername(
    BuildContext context,
    WidgetRef ref,
    String currentUsername,
  ) async {
    final saved = await showDialog<bool>(
      context: context,
      builder: (_) => _UsernameEditor(currentUsername: currentUsername),
    );
    if (saved == true && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Username updated successfully.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    final user = auth.user;
    final sections = <String, List<Widget>>{
      'Account': [
        if (_matches('Account Username edit name'))
          ListTile(
            key: const Key('edit-username'),
            leading: const Icon(Icons.alternate_email),
            title: const Text('Username'),
            subtitle: Text(user?.username ?? ''),
            trailing: const Icon(Icons.edit_outlined),
            onTap: user == null
                ? null
                : () => _editUsername(context, ref, user.username),
          ),
        if (_matches('Account security sign-in token secure device storage'))
          const ListTile(
            leading: Icon(Icons.verified_user_outlined),
            title: Text('Account security'),
            subtitle: Text(
              'Your sign-in token is stored in secure device storage.',
            ),
          ),
      ],
      'Imports and sync': [
        if (_matches(
          'Imports and sync Automatic M-PESA transactions View auto-sync status permissions and pending imports SMS mpesa m pesa history',
        ))
          ListTile(
            key: const Key('open-mpesa-import'),
            leading: const Icon(Icons.sms_outlined),
            title: const Text('Automatic M-PESA transactions'),
            subtitle: const Text(
              'View auto-sync status, permissions and pending imports.',
            ),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => const MpesaSettingsScreen(),
              ),
            ),
          ),
      ],
      'Privacy and permissions': [
        if (_matches(
          'Privacy and permissions manual entry CSV separately enabled M-PESA SMS import no direct bank connection',
        ))
          ListTile(
            key: const Key('view-privacy-summary'),
            leading: const Icon(Icons.privacy_tip_outlined),
            title: const Text('Privacy'),
            subtitle: const Text(
              'Manual entry, CSV and separately enabled M-PESA SMS import. '
              'No direct bank connection.',
            ),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => const PrivacyInfoScreen(),
              ),
            ),
          ),
        if (_matches(
          'Privacy and permissions Future model improvement optional de-identified training access app',
        ))
          SwitchListTile(
            key: const Key('model-training-choice'),
            secondary: const Icon(Icons.model_training_outlined),
            title: const Text('Future model improvement'),
            subtitle: const Text(
              'Optional permission for future de-identified model training. '
              'This does not affect your access to the app.',
            ),
            value: user?.modelTrainingOptIn ?? false,
            onChanged: auth.loading
                ? null
                : (value) async {
                    final saved = await ref
                        .read(authControllerProvider.notifier)
                        .updateConsent(modelTrainingOptIn: value);
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            saved
                                ? 'Your model-improvement choice was saved.'
                                : 'Could not save your choice.',
                          ),
                        ),
                      );
                    }
                  },
          ),
      ],
      'About and help': [
        if (_matches(
          'About and help View introduction again replay four Spendly welcome screens onboarding',
        ))
          ListTile(
            key: const Key('replay-onboarding'),
            leading: const Icon(Icons.slideshow_outlined),
            title: const Text('View introduction again'),
            subtitle: const Text('Replay the four Spendly welcome screens.'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => const OnboardingScreen(replay: true),
              ),
            ),
          ),
        if (_matches(
          'About and help Decision-support disclaimer insights planning professional financial advice fraud findings',
        ))
          const ListTile(
            leading: Icon(Icons.info_outline),
            title: Text('Decision-support disclaimer'),
            subtitle: Text(
              'Insights are planning support, not professional financial advice '
              'or fraud findings.',
            ),
          ),
        if (_matches('About and help App version build'))
          const AppVersionTile(),
      ],
    };
    return Scaffold(
      appBar: AppBar(title: const Text('Profile and settings')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
            child: TextField(
              key: const Key('settings-search'),
              controller: _search,
              autocorrect: false,
              enableSuggestions: false,
              textInputAction: TextInputAction.search,
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                labelText: 'Search settings',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _search.text.isEmpty
                    ? null
                    : IconButton(
                        tooltip: 'Clear settings search',
                        onPressed: () => setState(_search.clear),
                        icon: const Icon(Icons.clear),
                      ),
              ),
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (_search.text.trim().isEmpty) ...[
                  SoftPanel(
                    child: Column(
                      children: [
                        CircleAvatar(
                          radius: 36,
                          backgroundColor: AppColors.mint,
                          child: Text(
                            (user?.username.isNotEmpty ?? false)
                                ? user!.username.substring(0, 1).toUpperCase()
                                : '?',
                            style: Theme.of(context).textTheme.headlineMedium
                                ?.copyWith(color: AppColors.primaryDark),
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          user?.username.isNotEmpty == true
                              ? '@${user!.username}'
                              : '',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        Text(
                          user?.email ?? '',
                          textAlign: TextAlign.center,
                          style: const TextStyle(color: AppColors.mutedInk),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                ],
                if (sections.values.every((items) => items.isEmpty))
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 24),
                    child: Text(
                      'No settings found. Try SMS, privacy or account.',
                    ),
                  ),
                for (final section in sections.entries)
                  if (section.value.isNotEmpty) ...[
                    Text(
                      section.key,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    SoftPanel(
                      padding: EdgeInsets.zero,
                      child: Column(children: section.value),
                    ),
                    const SizedBox(height: 20),
                  ],
                const SizedBox(height: 16),
                OutlinedButton.icon(
                  onPressed: () async {
                    try {
                      await ref.read(authControllerProvider.notifier).logout();
                    } catch (_) {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text(
                              'Could not sign out. Please try again.',
                            ),
                          ),
                        );
                      }
                      return;
                    }
                    if (context.mounted) {
                      Navigator.of(context).popUntil((route) => route.isFirst);
                    }
                  },
                  icon: const Icon(Icons.logout),
                  label: const Text('Sign out'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _UsernameEditor extends ConsumerStatefulWidget {
  const _UsernameEditor({required this.currentUsername});

  final String currentUsername;

  @override
  ConsumerState<_UsernameEditor> createState() => _UsernameEditorState();
}

class _UsernameEditorState extends ConsumerState<_UsernameEditor> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _controller;
  String? _saveError;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.currentUsername);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _saving = true;
      _saveError = null;
    });
    final success = await ref
        .read(authControllerProvider.notifier)
        .updateUsername(_controller.text);
    if (!mounted) return;
    if (success) {
      Navigator.of(context).pop(true);
    } else {
      setState(() {
        _saving = false;
        _saveError = ref.read(authControllerProvider).error;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Edit username'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextFormField(
              key: const Key('username-field'),
              controller: _controller,
              autofocus: true,
              maxLength: 30,
              autocorrect: false,
              textInputAction: TextInputAction.done,
              decoration: const InputDecoration(
                labelText: 'Username',
                prefixText: '@',
                helperText: 'Letters, numbers, and underscores only',
              ),
              validator: (value) {
                final username = value?.trim() ?? '';
                if (!RegExp(r'^[A-Za-z0-9_]{3,30}$').hasMatch(username)) {
                  return 'Use 3–30 letters, numbers, or underscores.';
                }
                if (username.toLowerCase() ==
                    widget.currentUsername.toLowerCase()) {
                  return 'That is already your username.';
                }
                return null;
              },
              onFieldSubmitted: _saving ? null : (_) => _save(),
            ),
            if (_saveError != null)
              Text(
                _saveError!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.of(context).pop(false),
          child: const Text('Cancel'),
        ),
        FilledButton(
          key: const Key('save-username'),
          onPressed: _saving ? null : _save,
          child: _saving
              ? const SizedBox.square(
                  dimension: 18,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Text('Save'),
        ),
      ],
    );
  }
}
