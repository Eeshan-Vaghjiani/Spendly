import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../controllers/providers.dart';

class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key, this.replay = false});

  final bool replay;

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  static const _pages = [
    _OnboardingPage(
      icon: Icons.waving_hand_outlined,
      title: 'Welcome to Spendly',
      body:
          'See your financial picture in one calm place, without connecting a bank account.',
    ),
    _OnboardingPage(
      icon: Icons.receipt_long_outlined,
      title: 'Track your spending',
      body:
          'Record or import transactions, organise categories, and review any time range.',
    ),
    _OnboardingPage(
      icon: Icons.auto_graph_outlined,
      title: 'Plan with budgets and forecasts',
      body:
          'Set practical budgets and use experimental forecasts as planning support—not guarantees.',
    ),
    _OnboardingPage(
      icon: Icons.notifications_active_outlined,
      title: 'Stay informed',
      body:
          'Review supportive insights and unusual-activity alerts. They may be wrong, so you stay in control.',
    ),
  ];

  final _controller = PageController();
  int _index = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _finish({required bool skipped}) async {
    if (widget.replay) {
      if (mounted) Navigator.of(context).pop();
      return;
    }
    final saved = await ref
        .read(authControllerProvider.notifier)
        .completeOnboarding(skipped: skipped);
    if (!saved && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            ref.read(authControllerProvider).error ??
                'Could not save your introduction progress. Try again.',
          ),
        ),
      );
    }
  }

  void _goTo(int page) {
    if (page < 0 || page >= _pages.length) return;
    final media = MediaQuery.of(context);
    if (media.disableAnimations || media.accessibleNavigation) {
      _controller.jumpToPage(page);
    } else {
      _controller.animateToPage(
        page,
        duration: const Duration(milliseconds: 260),
        curve: Curves.easeOutCubic,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final loading = ref.watch(authControllerProvider).loading;
    return CallbackShortcuts(
      bindings: {
        const SingleActivator(LogicalKeyboardKey.arrowLeft): () =>
            _goTo(_index - 1),
        const SingleActivator(LogicalKeyboardKey.arrowRight): () {
          if (_index < _pages.length - 1) _goTo(_index + 1);
        },
        const SingleActivator(LogicalKeyboardKey.escape): () =>
            _finish(skipped: true),
      },
      child: Focus(
        autofocus: true,
        child: Scaffold(
          appBar: widget.replay
              ? AppBar(title: const Text('Spendly introduction'))
              : null,
          body: SafeArea(
            child: Column(
              children: [
                Align(
                  alignment: Alignment.centerRight,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                    child: TextButton(
                      key: const Key('onboarding-skip'),
                      onPressed: loading ? null : () => _finish(skipped: true),
                      child: const Text('Skip'),
                    ),
                  ),
                ),
                Expanded(
                  child: PageView.builder(
                    controller: _controller,
                    itemCount: _pages.length,
                    onPageChanged: (value) => setState(() => _index = value),
                    itemBuilder: (context, index) =>
                        _PageContent(page: _pages[index], position: index + 1),
                  ),
                ),
                Semantics(
                  label: 'Introduction page ${_index + 1} of ${_pages.length}',
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(
                      _pages.length,
                      (index) => AnimatedContainer(
                        duration: MediaQuery.of(context).disableAnimations
                            ? Duration.zero
                            : const Duration(milliseconds: 180),
                        width: index == _index ? 26 : 8,
                        height: 8,
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        decoration: BoxDecoration(
                          color: index == _index
                              ? AppColors.primary
                              : AppColors.outline,
                          borderRadius: BorderRadius.circular(99),
                        ),
                      ),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(24, 24, 24, 28),
                  child: Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          key: const Key('onboarding-back'),
                          onPressed: _index == 0 || loading
                              ? null
                              : () => _goTo(_index - 1),
                          child: const Text('Back'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: FilledButton(
                          key: Key(
                            _index == _pages.length - 1
                                ? 'onboarding-get-started'
                                : 'onboarding-next',
                          ),
                          onPressed: loading
                              ? null
                              : () {
                                  if (_index == _pages.length - 1) {
                                    _finish(skipped: false);
                                  } else {
                                    _goTo(_index + 1);
                                  }
                                },
                          child: loading
                              ? const SizedBox.square(
                                  dimension: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : Text(
                                  _index == _pages.length - 1
                                      ? 'Get Started'
                                      : 'Next',
                                ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _OnboardingPage {
  const _OnboardingPage({
    required this.icon,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final String title;
  final String body;
}

class _PageContent extends StatelessWidget {
  const _PageContent({required this.page, required this.position});

  final _OnboardingPage page;
  final int position;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 12),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 520),
          child: Column(
            children: [
              Container(
                width: 148,
                height: 148,
                decoration: BoxDecoration(
                  color: AppColors.mint.withValues(alpha: .65),
                  borderRadius: BorderRadius.circular(38),
                ),
                child: Icon(page.icon, size: 72, color: AppColors.primaryDark),
              ),
              const SizedBox(height: 34),
              Text(
                page.title,
                key: Key('onboarding-title-$position'),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 14),
              Text(
                page.body,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: AppColors.mutedInk,
                  height: 1.5,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
