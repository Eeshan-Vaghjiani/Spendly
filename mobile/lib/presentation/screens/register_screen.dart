import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../controllers/providers.dart';
import '../widgets/brand_logo.dart';
import 'consent_setup_screen.dart';
import 'login_screen.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key, this.isRoot = false});

  final bool isRoot;

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  bool _hidePassword = true;

  bool get _hasLength => _password.text.length >= 10;
  bool get _hasUppercase => _password.text.contains(RegExp('[A-Z]'));
  bool get _hasLowercase => _password.text.contains(RegExp('[a-z]'));
  bool get _hasNumber => _password.text.contains(RegExp('[0-9]'));
  bool get _hasSymbol =>
      _password.text.contains(RegExp(r'[!@#$%^&*(),.?":{}|<>_+\-=\[\]\/;`~]'));
  bool get _hasNoSpaces => !_password.text.contains(RegExp(r'\s'));
  bool get _passwordIsStrong =>
      _hasLength &&
      _hasUppercase &&
      _hasLowercase &&
      _hasNumber &&
      _hasSymbol &&
      _hasNoSpaces;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => ConsentSetupScreen.registration(
          email: _email.text.trim(),
          password: _password.text,
          displayName: _name.text.trim(),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authControllerProvider);
    return Scaffold(
      appBar: widget.isRoot
          ? null
          : AppBar(title: const Text('Create account')),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (widget.isRoot) ...[
                    const Align(child: BrandLogo(size: 88)),
                    const SizedBox(height: 16),
                    Text(
                      'Create your account',
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Start with one week of transactions. Your forecast will '
                      'learn as you add more history.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 24),
                  ],
                  Align(
                    alignment: Alignment.centerLeft,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 11,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.mint.withValues(alpha: .55),
                        borderRadius: BorderRadius.circular(99),
                      ),
                      child: const Text(
                        'Step 1 of 2 · Account details',
                        style: TextStyle(
                          color: AppColors.primaryDark,
                          fontWeight: FontWeight.w700,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    key: const Key('register-display-name'),
                    controller: _name,
                    decoration: const InputDecoration(
                      labelText: 'Display name',
                    ),
                    textCapitalization: TextCapitalization.words,
                    textInputAction: TextInputAction.next,
                    validator: (value) {
                      final name = value?.trim() ?? '';
                      if (name.length < 2) {
                        return 'Enter at least 2 characters.';
                      }
                      if (name.length > 100) {
                        return 'Use 100 characters or fewer.';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    key: const Key('register-email'),
                    controller: _email,
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.next,
                    autocorrect: false,
                    decoration: const InputDecoration(
                      labelText: 'Email address',
                      prefixIcon: Icon(Icons.mail_outline),
                    ),
                    validator: (value) {
                      final email = value?.trim() ?? '';
                      final valid = RegExp(
                        r'^[^\s@]+@[^\s@]+\.[^\s@]+$',
                      ).hasMatch(email);
                      return valid ? null : 'Enter a complete email address.';
                    },
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    key: const Key('register-password'),
                    controller: _password,
                    obscureText: _hidePassword,
                    autocorrect: false,
                    enableSuggestions: false,
                    onChanged: (_) => setState(() {}),
                    decoration: InputDecoration(
                      labelText: 'Create password',
                      prefixIcon: const Icon(Icons.lock_outline),
                      suffixIcon: IconButton(
                        tooltip: _hidePassword
                            ? 'Show password'
                            : 'Hide password',
                        onPressed: () =>
                            setState(() => _hidePassword = !_hidePassword),
                        icon: Icon(
                          _hidePassword
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined,
                        ),
                      ),
                    ),
                    validator: (_) => _passwordIsStrong
                        ? null
                        : 'Complete all password rules below.',
                  ),
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: AppColors.surface,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: AppColors.outline),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Your password must have:',
                          style: TextStyle(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 10,
                          runSpacing: 7,
                          children: [
                            _PasswordRule(
                              label: '10+ characters',
                              met: _hasLength,
                            ),
                            _PasswordRule(
                              label: 'Uppercase',
                              met: _hasUppercase,
                            ),
                            _PasswordRule(
                              label: 'Lowercase',
                              met: _hasLowercase,
                            ),
                            _PasswordRule(label: 'Number', met: _hasNumber),
                            _PasswordRule(label: 'Symbol', met: _hasSymbol),
                            _PasswordRule(
                              label: 'No spaces',
                              met: _hasNoSpaces,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  if (auth.error != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      auth.error!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  FilledButton(
                    key: const Key('register-continue'),
                    onPressed: auth.loading ? null : _submit,
                    child: const Text('Continue'),
                  ),
                  if (widget.isRoot)
                    TextButton(
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => const LoginScreen(),
                        ),
                      ),
                      child: const Text('Already have an account? Sign in'),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _PasswordRule extends StatelessWidget {
  const _PasswordRule({required this.label, required this.met});

  final String label;
  final bool met;

  @override
  Widget build(BuildContext context) {
    final color = met ? AppColors.income : AppColors.mutedInk;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          met ? Icons.check_circle : Icons.radio_button_unchecked,
          size: 16,
          color: color,
        ),
        const SizedBox(width: 5),
        Text(label, style: TextStyle(color: color, fontSize: 12)),
      ],
    );
  }
}
