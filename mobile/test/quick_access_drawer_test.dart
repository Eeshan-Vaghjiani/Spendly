import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/data/models/models.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/home_shell.dart';
import 'package:spending_support/presentation/widgets/quick_access_drawer.dart';

import 'widget_test.dart' show FakeRepository, appWith;

const _firstUser = UserProfile(
  id: 'drawer-user',
  email: 'drawer@example.com',
  displayName: 'Drawer User',
  username: 'drawer_user',
);

Finder get _shellScaffold => find
    .descendant(of: find.byType(HomeShell), matching: find.byType(Scaffold))
    .first;

void main() {
  testWidgets('drawer selects existing tabs without pushing routes', (
    tester,
  ) async {
    await tester.pumpWidget(appWith(FakeRepository(restoredUser: _firstUser)));
    await tester.pumpAndSettle();

    for (var index = 1; index < 5; index++) {
      await tester.tap(find.byKey(const Key('open-quick-access')));
      await tester.pumpAndSettle();
      final scaffold = tester.state<ScaffoldState>(_shellScaffold);
      expect(scaffold.isDrawerOpen, isTrue);
      expect(
        tester
            .widget<ListTile>(find.byKey(const Key('quick-access-0')))
            .selected,
        isTrue,
      );

      await tester.tap(find.byKey(Key('quick-access-$index')));
      await tester.pumpAndSettle();
      expect(scaffold.isDrawerOpen, isFalse);
      expect(
        tester.widget<NavigationBar>(find.byType(NavigationBar)).selectedIndex,
        index,
      );
      expect(find.byType(HomeShell), findsOneWidget);
      expect(
        Navigator.of(tester.element(find.byType(HomeShell))).canPop(),
        isFalse,
      );

      // The retained bottom bar returns to the same dashboard tab.
      await tester.tap(find.byType(NavigationDestination).first);
      await tester.pumpAndSettle();
      expect(
        tester.widget<NavigationBar>(find.byType(NavigationBar)).selectedIndex,
        0,
      );
    }
  });

  testWidgets('selecting the current drawer tab only closes the drawer', (
    tester,
  ) async {
    final repository = FakeRepository(restoredUser: _firstUser);
    await tester.pumpWidget(appWith(repository));
    await tester.pumpAndSettle();
    final calls = repository.dashboardSummaryCalls;

    await tester.tap(find.byKey(const Key('open-quick-access')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('quick-access-0')));
    await tester.pumpAndSettle();

    expect(tester.state<ScaffoldState>(_shellScaffold).isDrawerOpen, isFalse);
    expect(repository.dashboardSummaryCalls, calls);
    expect(
      Navigator.of(tester.element(find.byType(HomeShell))).canPop(),
      isFalse,
    );
  });

  testWidgets('account changes reset the selected tab and open drawer', (
    tester,
  ) async {
    await tester.pumpWidget(appWith(FakeRepository(restoredUser: _firstUser)));
    await tester.pumpAndSettle();
    final container = ProviderScope.containerOf(
      tester.element(find.byType(HomeShell)),
    );
    await tester.tap(find.byKey(const Key('open-quick-access')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('quick-access-1')));
    await tester.pumpAndSettle();
    tester.state<ScaffoldState>(_shellScaffold).openDrawer();
    await tester.pumpAndSettle();

    // FakeRepository.login returns a different account from the restored one.
    await container
        .read(authControllerProvider.notifier)
        .login('eva@example.com', 'test-password');
    await tester.pumpAndSettle();

    expect(
      tester.widget<NavigationBar>(find.byType(NavigationBar)).selectedIndex,
      0,
    );
    expect(tester.state<ScaffoldState>(_shellScaffold).isDrawerOpen, isFalse);
    expect(find.text('Hello, eva'), findsOneWidget);
    expect(find.text('Hello, drawer_user'), findsNothing);
    expect(
      Navigator.of(tester.element(find.byType(HomeShell))).canPop(),
      isFalse,
    );
  });

  testWidgets('back dismisses the drawer and preserves the active tab', (
    tester,
  ) async {
    await tester.pumpWidget(appWith(FakeRepository(restoredUser: _firstUser)));
    await tester.pumpAndSettle();
    await tester.tap(find.byType(NavigationDestination).at(2));
    await tester.pumpAndSettle();
    tester.state<ScaffoldState>(_shellScaffold).openDrawer();
    await tester.pumpAndSettle();
    expect(
      tester.widget<ListTile>(find.byKey(const Key('quick-access-2'))).selected,
      isTrue,
    );

    await tester.binding.handlePopRoute();
    await tester.pumpAndSettle();

    expect(tester.state<ScaffoldState>(_shellScaffold).isDrawerOpen, isFalse);
    expect(
      tester.widget<NavigationBar>(find.byType(NavigationBar)).selectedIndex,
      2,
    );
  });

  testWidgets('drawer scrolls on small screens with large text', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(320, 400));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    int? selected;
    await tester.pumpWidget(
      MaterialApp(
        home: MediaQuery(
          data: const MediaQueryData(textScaler: TextScaler.linear(2)),
          child: Scaffold(
            body: QuickAccessDrawer(
              selectedIndex: 0,
              onDestinationSelected: (value) => selected = value,
            ),
          ),
        ),
      ),
    );
    await tester.scrollUntilVisible(
      find.byKey(const Key('quick-access-4')),
      120,
    );
    await tester.tap(find.byKey(const Key('quick-access-4')));
    expect(selected, 4);
    expect(tester.takeException(), isNull);
  });
}
