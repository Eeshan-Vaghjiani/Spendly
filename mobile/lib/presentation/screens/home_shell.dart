import 'package:flutter/material.dart';

import '../widgets/quick_access_drawer.dart';
import 'budget_screen.dart';
import 'analytics_screen.dart';
import 'dashboard_screen.dart';
import 'more_screen.dart';
import 'transaction_history_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  final _scaffoldKey = GlobalKey<ScaffoldState>();
  int _index = 0;
  int _pageVersion = 0;

  late final _screens = [
    DashboardScreen(onOpenMenu: () => _scaffoldKey.currentState?.openDrawer()),
    const TransactionHistoryScreen(),
    const BudgetScreen(),
    const AnalyticsScreen(),
    const MoreScreen(),
  ];

  void _selectDestination(int value) {
    setState(() {
      _index = value;
      _pageVersion += 1;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey,
      drawer: QuickAccessDrawer(
        selectedIndex: _index,
        onDestinationSelected: (value) {
          _scaffoldKey.currentState?.closeDrawer();
          if (value != _index) _selectDestination(value);
        },
      ),
      body: KeyedSubtree(key: ValueKey(_pageVersion), child: _screens[_index]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: _selectDestination,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.receipt_long_outlined),
            selectedIcon: Icon(Icons.receipt_long),
            label: 'Transactions',
          ),
          NavigationDestination(
            icon: Icon(Icons.savings_outlined),
            selectedIcon: Icon(Icons.savings),
            label: 'Budgets',
          ),
          NavigationDestination(
            icon: Icon(Icons.show_chart_outlined),
            selectedIcon: Icon(Icons.show_chart),
            label: 'Analytics',
          ),
          NavigationDestination(icon: Icon(Icons.more_horiz), label: 'More'),
        ],
      ),
    );
  }
}
