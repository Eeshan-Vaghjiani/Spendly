import 'package:flutter/material.dart';

/// Shortcuts to the root shell's tabs; selection is owned by the shell.
class QuickAccessDrawer extends StatelessWidget {
  const QuickAccessDrawer({
    super.key,
    required this.selectedIndex,
    required this.onDestinationSelected,
  });

  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;

  static const _destinations = [
    (label: 'Dashboard', icon: Icons.dashboard_outlined),
    (label: 'Transactions', icon: Icons.receipt_long_outlined),
    (label: 'Budgets', icon: Icons.savings_outlined),
    (label: 'Analytics', icon: Icons.show_chart_outlined),
    (label: 'More', icon: Icons.more_horiz),
  ];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Drawer(
      semanticLabel: 'Quick access',
      child: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(12),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
              child: Text('Spendly', style: theme.textTheme.headlineSmall),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Text('Quick access', style: theme.textTheme.titleMedium),
            ),
            const Divider(),
            for (var index = 0; index < _destinations.length; index++)
              ListTile(
                key: Key('quick-access-$index'),
                leading: Icon(_destinations[index].icon),
                title: Text(_destinations[index].label),
                selected: index == selectedIndex,
                selectedTileColor: theme.colorScheme.secondaryContainer,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                onTap: () => onDestinationSelected(index),
              ),
          ],
        ),
      ),
    );
  }
}
