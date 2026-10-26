"""Native CSV recovery on one named disposable emulator and loopback fixture.

Build tool/csv_recovery_main.dart as a separate debug acceptance APK first.
Start backend.scripts.run_csv_recovery_backend and the named AVD, then run this.
The acceptance package is disposable; the original Spendly package is untouched.
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SDK = Path.home() / 'AppData/Local/Android/Sdk'
ADB = SDK / 'platform-tools/adb.exe'
APK = ROOT / 'mobile/build/app/outputs/flutter-apk/app-debug.apk'
SERIAL = 'emulator-5564'
PACKAGE = 'com.evagh.capstone.spending_support.acceptance'
PICKERS = {'com.google.android.documentsui', 'com.android.documentsui'}
BASE = 'http://127.0.0.1:5057/api/v1'
FILENAME = 'spendly-csv-recovery.csv'
XML = '/sdcard/spendly-csv-recovery-ui.xml'


def adb(*args, timeout=30, check=True):
    result = subprocess.run([str(ADB), '-s', SERIAL, *args], capture_output=True,
                            text=True, encoding='utf-8', timeout=timeout)
    if check and result.returncode:
        raise RuntimeError('Disposable ADB command failed: ' + result.stderr[:300])
    return result.stdout.strip()


def api(path, *, body=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(BASE + path, headers=headers,
                                 data=None if body is None else json.dumps(body).encode())
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)['data']


def wait_for(check, description, seconds=60):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        value = check()
        if value:
            return value
        time.sleep(0.7)
    raise RuntimeError('Timed out: ' + description)


def nodes():
    # Android may have no accessibility root while a new activity starts.
    # Never reuse an older tree as evidence for the new screen.
    adb('shell', 'rm', '-f', XML)
    result = adb('shell', 'uiautomator', 'dump', XML, check=False)
    if 'UI hierchary dumped to:' not in result:
        return []
    return list(ET.fromstring(adb('shell', 'cat', XML)).iter('node'))


def label(node):
    return (node.get('text', '') + '\n' + node.get('content-desc', '')).strip()


def tap(node):
    if node.get('package') not in PICKERS | {PACKAGE}:
        raise RuntimeError('Refusing input outside acceptance app/document picker.')
    match = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.get('bounds', ''))
    if not match or node.get('enabled') != 'true':
        raise RuntimeError('Observed control is unavailable.')
    x1, y1, x2, y2 = map(int, match.groups())
    adb('shell', 'input', 'tap', str((x1+x2)//2), str((y1+y2)//2))


def control(text):
    return next((n for n in nodes() if n.get('package') == PACKAGE
                 and text in label(n).splitlines() and n.get('enabled') == 'true'), None)


def tap_app(text):
    tap(wait_for(lambda: control(text), 'app control ' + text))


def launch():
    result = adb('shell', 'am', 'start', '-W', '-n',
                 PACKAGE + '/com.evagh.capstone.spending_support.MainActivity')
    if 'Error' in result:
        raise RuntimeError('Acceptance activity did not start: ' + result)


def open_upload():
    tap_app('More')
    tap_app('Import transactions')
    wait_for(lambda: control('Choose CSV file'), 'upload screen')


def open_picker():
    tap_app('Choose CSV file')
    return wait_for(lambda: next((n.get('package') for n in nodes()
                                 if n.get('package') in PICKERS), None), 'document picker')


def choose():
    for _ in range(15):
        picker = [n for n in nodes() if n.get('package') in PICKERS]
        file = next((n for n in picker if n.get('text') == FILENAME), None)
        if file is not None:
            tap(file)
            return
        downloads = next((n for n in picker if n.get('text') == 'Downloads'), None)
        roots = next((n for n in picker if n.get('content-desc') == 'Show roots'), None)
        if downloads is not None:
            tap(downloads)
        elif roots is not None:
            tap(roots)
        time.sleep(0.5)
    raise RuntimeError('Synthetic CSV not found in picker.')


def checkpoint(name):
    print('CSV_RECOVERY:' + name + ':passed', flush=True)


def main():
    if sys.flags.optimize:
        raise RuntimeError('Run without -O; acceptance assertions must remain enabled.')
    if adb('shell', 'getprop', 'ro.hardware') not in {'ranchu', 'goldfish'}:
        raise RuntimeError('Only a disposable emulator is allowed.')
    if adb('emu', 'avd', 'name').splitlines()[0] != 'SpendlySmsFinal_20261023':
        raise RuntimeError('Wrong disposable AVD.')
    wait_for(lambda: adb('shell', 'getprop', 'sys.boot_completed') == '1', 'boot')
    badging = subprocess.check_output(
        [str(SDK / 'build-tools/36.0.0/aapt.exe'), 'dump', 'badging', str(APK)], text=True)
    if "package: name='" + PACKAGE + "'" not in badging or 'android.permission.READ_SMS' in badging:
        raise RuntimeError('Only the separate no-SMS acceptance APK is allowed.')
    marker = api('/csv-recovery-target')
    if (marker.get('disposable') is not True or marker.get('database') != 'in_memory'
            or marker.get('scenario') != 'csv_recovery' or marker.get('starts') != []):
        raise RuntimeError('Start a fresh in-memory CSV fixture.')
    token = api('/auth/login', body={'email': 'csv-recovery@example.invalid',
                                   'password': 'SyntheticNativeOnly123!'})['access_token']

    def count():
        return api('/transactions', token=token)['total']

    assert count() == 0
    try:
        # Only this lab package on the verified synthetic emulator is reset.
        adb('uninstall', PACKAGE, check=False)
        assert 'Success' in adb('install', str(APK), timeout=120)
        print('CSV_RECOVERY:acceptance-apk-installed', flush=True)
        adb('reverse', 'tcp:5057', 'tcp:5057')
        with tempfile.TemporaryDirectory(prefix='spendly-csv-recovery-') as directory:
            csv = Path(directory) / FILENAME
            csv.write_text('transaction_timestamp,amount,category,transaction_type,merchant,is_recurring\n'
                           '2026-10-19T12:00:00+03:00,125.50,food,expense,Synthetic recovery shop,false\n',
                           encoding='utf-8')
            adb('push', str(csv), '/sdcard/Download/' + FILENAME)
            adb('shell', 'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE',
                '-d', 'file:///sdcard/Download/' + FILENAME)
        launch()
        wait_for(lambda: len(api('/csv-recovery-target')['starts']) == 1,
                 'first synthetic startup', seconds=180)
        open_upload()
        assert api('/csv-recovery-target')['starts'] == [{'restored': False}]
        open_picker()
        before = adb('shell', 'pidof', PACKAGE, check=False)
        assert before, 'App must be running before process kill'
        adb('shell', 'am', 'kill', PACKAGE)
        wait_for(lambda: not adb('shell', 'pidof', PACKAGE, check=False), 'background app death')
        choose()
        wait_for(lambda: len(api('/csv-recovery-target')['starts']) == 2,
                 'restored startup', seconds=180)
        assert api('/csv-recovery-target')['starts'][-1]['restored'] is True
        assert count() == 0, 'Interrupted selection must not create an unsolicited upload'
        assert api('/csv-recovery-target')['uploads'] == []
        checkpoint('process-death-session-restored-no-upload')
        open_upload()
        open_picker()
        choose()
        wait_for(lambda: len(api('/csv-recovery-target')['uploads']) == 1, 'first upload response')
        wait_for(lambda: control('Upload summary'), 'successful retry summary')
        assert count() == 1
        assert api('/csv-recovery-target')['uploads'][-1] == {
            'received_rows': 1, 'created_rows': 1, 'duplicate_rows': 0, 'invalid_rows': 0}
        checkpoint('retry-after-process-death')
        picker = open_picker()
        app_pid = adb('shell', 'pidof', PACKAGE, check=False)
        adb('shell', 'am', 'force-stop', picker)
        wait_for(lambda: control('Choose CSV file'), 'usable upload button after provider stop')
        assert adb('shell', 'pidof', PACKAGE, check=False) == app_pid
        open_picker()
        choose()
        wait_for(lambda: len(api('/csv-recovery-target')['uploads']) == 2, 'second upload response')
        wait_for(lambda: control('Upload summary'), 'duplicate retry summary')
        assert count() == 1
        assert api('/csv-recovery-target')['uploads'][-1] == {
            'received_rows': 1, 'created_rows': 0, 'duplicate_rows': 1, 'invalid_rows': 0}
        checkpoint('provider-interruption-and-duplicate-retry')
        starts_before = len(api('/csv-recovery-target')['starts'])
        assert 'Success' in adb('install', '-r', str(APK), timeout=120)
        launch()
        wait_for(lambda: len(api('/csv-recovery-target')['starts']) == starts_before + 1,
                 'session restored after in-place reinstall', seconds=180)
        wait_for(lambda: control('More'), 'signed-in dashboard after reinstall')
        assert api('/csv-recovery-target')['starts'][-1]['restored'] is True
        assert count() == 1
        checkpoint('in-place-reinstall-preserves-session-and-record')
    finally:
        adb('shell', 'rm', '-f', '/sdcard/Download/' + FILENAME, XML, check=False)
        adb('uninstall', PACKAGE, check=False)
        adb('reverse', '--remove', 'tcp:5057', check=False)


if __name__ == '__main__':
    main()
