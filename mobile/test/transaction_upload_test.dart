import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:spending_support/core/network/api_exception.dart';
import 'package:spending_support/presentation/controllers/providers.dart';
import 'package:spending_support/presentation/screens/transaction_upload_screen.dart';

import 'widget_test.dart' show FakeRepository;

class SyntheticPicker extends FilePicker {
  Future<FilePickerResult?> Function() pick = () async => null;
  int calls = 0;

  @override
  Future<FilePickerResult?> pickFiles({
    String? dialogTitle,
    String? initialDirectory,
    FileType type = FileType.any,
    List<String>? allowedExtensions,
    Function(FilePickerStatus)? onFileLoading,
    bool allowCompression = false,
    int compressionQuality = 0,
    bool allowMultiple = false,
    bool withData = false,
    bool withReadStream = false,
    bool lockParentWindow = false,
    bool readSequential = false,
  }) {
    calls++;
    return pick();
  }
}

class UploadRepository extends FakeRepository {
  int uploads = 0;
  Future<Map<String, dynamic>> Function() upload = () async => {
    'received_rows': 4,
    'created_rows': 2,
    'duplicate_rows': 1,
    'invalid_rows': 1,
  };

  @override
  Future<Map<String, dynamic>> uploadTransactions(String path) {
    uploads++;
    return upload();
  }
}

FilePickerResult selectedFile({String? path = '/synthetic/fixture.csv'}) =>
    FilePickerResult([
      PlatformFile(name: 'fixture.csv', size: 100, path: path),
    ]);

void main() {
  late SyntheticPicker picker;
  late UploadRepository repository;
  setUp(() {
    picker = SyntheticPicker();
    FilePicker.platform = picker;
    repository = UploadRepository();
  });

  Future<void> showUpload(WidgetTester tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [repositoryProvider.overrideWithValue(repository)],
        child: const MaterialApp(home: TransactionUploadScreen()),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets(
    'cancelled picker re-enables button and duplicate taps do not open it twice',
    (tester) async {
      final pending = Completer<FilePickerResult?>();
      picker.pick = () => pending.future;
      await showUpload(tester);
      await tester.tap(find.text('Choose CSV file'));
      await tester.tap(find.text('Choose CSV file'));
      await tester.pump();
      expect(
        tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNull,
      );
      expect(picker.calls, 1);
      pending.complete(null);
      await tester.pumpAndSettle();
      expect(repository.uploads, 0);
      expect(
        tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
        isNotNull,
      );
    },
  );

  testWidgets('picker failure is safe and retry uploads summary', (
    tester,
  ) async {
    picker.pick = () async =>
        throw PlatformException(code: 'fixture', message: '/private/path');
    await showUpload(tester);
    await tester.tap(find.text('Choose CSV file'));
    await tester.pumpAndSettle();
    expect(
      find.textContaining('could not be selected or uploaded'),
      findsOneWidget,
    );
    expect(find.textContaining('/private/path'), findsNothing);
    picker.pick = () async => selectedFile();
    await tester.tap(find.text('Choose CSV file'));
    await tester.pumpAndSettle();
    expect(find.text('Upload summary'), findsOneWidget);
    expect(find.text('Rows created'), findsOneWidget);
    expect(repository.uploads, 1);
  });

  testWidgets('unavailable file path does not submit', (tester) async {
    picker.pick = () async => selectedFile(path: null);
    await showUpload(tester);
    await tester.tap(find.text('Choose CSV file'));
    await tester.pumpAndSettle();
    expect(
      find.textContaining('Choose a CSV saved on this device'),
      findsOneWidget,
    );
    expect(repository.uploads, 0);
  });

  testWidgets('failed upload shows safe error and allows an explicit retry', (
    tester,
  ) async {
    picker.pick = () async => selectedFile();
    repository.upload = () async => throw const ApiException(
      'NETWORK_ERROR',
      'Reconnect and check before retrying.',
    );
    await showUpload(tester);
    await tester.tap(find.text('Choose CSV file'));
    await tester.pumpAndSettle();
    expect(find.text('Reconnect and check before retrying.'), findsOneWidget);
    expect(repository.uploads, 1);
    expect(
      tester.widget<FilledButton>(find.byType(FilledButton)).onPressed,
      isNotNull,
    );
  });

  testWidgets(
    'leaving while picker is open does not upload or update disposed screen',
    (tester) async {
      final pending = Completer<FilePickerResult?>();
      picker.pick = () => pending.future;
      await showUpload(tester);
      await tester.tap(find.text('Choose CSV file'));
      await tester.pumpWidget(const SizedBox());
      pending.complete(selectedFile());
      await tester.pumpAndSettle();
      expect(repository.uploads, 0);
      expect(tester.takeException(), isNull);
    },
  );

  for (final fails in [false, true]) {
    testWidgets(
      'leaving during upload ignores late ${fails ? 'failure' : 'success'}',
      (tester) async {
        final pending = Completer<Map<String, dynamic>>();
        picker.pick = () async => selectedFile();
        repository.upload = () => pending.future;
        await showUpload(tester);
        await tester.tap(find.text('Choose CSV file'));
        await tester.pump();
        expect(repository.uploads, 1);
        await tester.pumpWidget(const SizedBox());
        if (fails) {
          pending.completeError(
            const ApiException('NETWORK_ERROR', 'Connection interrupted.'),
          );
        } else {
          pending.complete({'created_rows': 1});
        }
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);
      },
    );
  }

  testWidgets('CSV help contains the exact headers and timezone example', (
    tester,
  ) async {
    await showUpload(tester);
    await tester.tap(find.byKey(const Key('csv-format-help')));
    await tester.pumpAndSettle();
    final example = tester
        .widget<SelectableText>(find.byKey(const Key('csv-example')))
        .data!;
    expect(
      example.split('\n').first,
      'transaction_timestamp,amount,category,transaction_type,merchant,is_recurring',
    );
    expect(example, contains('2026-10-19T12:30:00+03:00'));
    expect(example, contains(',125.50,food,expense,Synthetic shop,false'));
  });

  testWidgets('rejected rows show numbers, reasons and correction guidance', (
    tester,
  ) async {
    picker.pick = () async => selectedFile();
    repository.upload = () async => {
      'received_rows': 3,
      'created_rows': 1,
      'duplicate_rows': 1,
      'invalid_rows': 1,
      'errors': [
        {'row': 4, 'message': 'Amount must have at most two decimal places.'},
      ],
    };
    await showUpload(tester);
    await tester.tap(find.text('Choose CSV file'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.text('Row 4: Amount must have at most two decimal places.'),
      250,
    );
    expect(
      find.text('Row 4: Amount must have at most two decimal places.'),
      findsOneWidget,
    );
    expect(find.textContaining('header as row 1'), findsOneWidget);
    expect(find.textContaining('skipped as duplicates'), findsOneWidget);
    expect(repository.uploads, 1);
  });

  testWidgets('many long errors stay bounded and fit 200 percent text', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    tester.platformDispatcher.textScaleFactorTestValue = 2;
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
    picker.pick = () async => selectedFile();
    repository.upload = () async => {
      'received_rows': 25,
      'created_rows': 0,
      'duplicate_rows': 0,
      'invalid_rows': 25,
      'errors': List.generate(
        25,
        (index) => {'row': index + 2, 'message': 'Invalid amount. ' * 100},
      ),
    };
    await showUpload(tester);
    await tester.scrollUntilVisible(find.text('Choose CSV file'), 200);
    await tester.tap(find.text('Choose CSV file'));
    await tester.pumpAndSettle();
    // Jump through the long, bounded report rather than relying on a fixed
    // number of drags; each entry must remain readable without an overflow.
    final scroll = tester.state<ScrollableState>(find.byType(Scrollable).first);
    while (scroll.position.extentAfter > 0) {
      scroll.position.jumpTo(
        (scroll.position.pixels + 500).clamp(
          0,
          scroll.position.maxScrollExtent,
        ),
      );
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    }
    expect(find.textContaining('first 20 of 25 rejected rows'), findsOneWidget);
    expect(find.textContaining('Row 22:'), findsNothing);
    expect(repository.uploads, 1);
  });

  testWidgets('missing row details has a useful fallback', (tester) async {
    picker.pick = () async => selectedFile();
    await showUpload(tester);
    await tester.tap(find.text('Choose CSV file'));
    await tester.pumpAndSettle();
    await tester.scrollUntilVisible(
      find.textContaining('Row details were not returned'),
      250,
    );
    expect(find.textContaining('Check the CSV format'), findsOneWidget);
  });

  testWidgets(
    'expanded CSV example scrolls on a narrow screen at 200 percent',
    (tester) async {
      tester.view.physicalSize = const Size(320, 640);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      tester.platformDispatcher.textScaleFactorTestValue = 2;
      addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
      await showUpload(tester);
      await tester.scrollUntilVisible(find.text('CSV format and example'), 200);
      await tester.pumpAndSettle();
      await tester.tap(find.text('CSV format and example'));
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.byKey(const Key('csv-example')),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.byKey(const Key('csv-example')), findsOneWidget);
      await tester.scrollUntilVisible(
        find.text('Choose CSV file'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      expect(tester.takeException(), isNull);
    },
  );
}
