"""Drive only invented CSV fixtures on the named disposable Android emulator.

Start beside the opt-in native CSV integration test. Watches that test's stdout
log for checkpoints; never accepts a personal device or hosted backend URL.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ADB = Path.home() / 'AppData/Local/Android/Sdk/platform-tools/adb.exe'
SERIAL = 'emulator-5564'


def adb(*args):
    result = subprocess.run([str(ADB), '-s', SERIAL, *args],
                            capture_output=True, text=True, encoding='utf-8', timeout=25)
    if result.returncode:
        raise RuntimeError('Disposable emulator command failed: ' + result.stderr[:300])
    return result.stdout


def nodes():
    adb('shell', 'uiautomator', 'dump', '/sdcard/spendly-picker-ui.xml')
    current = list(ET.fromstring(adb('shell', 'cat', '/sdcard/spendly-picker-ui.xml')).iter('node'))
    waiting = next((n for n in current if n.get('resource-id') == 'android:id/aerr_wait'), None)
    if waiting is not None:
        tap(waiting)
        print('CSV_LAB:waited_for_emulator_system_ui', flush=True)
        return []
    return current


def tap(node):
    coordinates = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.get('bounds', ''))
    if not coordinates:
        raise RuntimeError('Picker control has no observed bounds.')
    x1, y1, x2, y2 = map(int, coordinates.groups())
    adb('shell', 'input', 'tap', str((x1+x2)//2), str((y1+y2)//2))


def choose(filename):
    for _ in range(20):
        current = nodes()
        # Inputs only belong to the system document picker, never another app.
        picker = [n for n in current if n.get('package') in {
            'com.google.android.documentsui', 'com.android.documentsui'}]
        match = next((n for n in picker if n.get('text') == filename), None)
        if match is not None:
            tap(match)
            return
        downloads = next((n for n in picker if n.get('text') == 'Downloads'), None)
        if downloads is not None:
            tap(downloads)
        else:
            roots = next((n for n in picker if n.get('content-desc') == 'Show roots'), None)
            if roots is not None:
                tap(roots)
        time.sleep(0.5)
    raise RuntimeError('Synthetic CSV was not available in the system picker.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', required=True)
    args = parser.parse_args()
    log = Path(args.log).resolve()
    if not log.is_relative_to(ROOT / 'tmp'):
        raise RuntimeError('Only a test stdout log under this workspace tmp is allowed.')
    if adb('shell', 'getprop', 'ro.hardware').strip() not in {'ranchu', 'goldfish'}:
        raise RuntimeError('Only the disposable emulator is allowed.')
    if adb('emu', 'avd', 'name').splitlines()[0].strip() != 'SpendlySmsFinal_20261023':
        raise RuntimeError('Unexpected AVD; do not use a personal device.')
    for _ in range(60):
        if adb('shell', 'getprop', 'sys.boot_completed').strip() == '1':
            break
        time.sleep(1)
    else:
        raise RuntimeError('Disposable emulator has not finished booting.')
    with urllib.request.urlopen('http://127.0.0.1:5057/api/v1/acceptance-target', timeout=5) as response:
        target = json.load(response)['data']
    if target.get('disposable') is not True or target.get('database') != 'in_memory':
        raise RuntimeError('Disposable backend attestation failed.')
    fixtures = {
        'spendly-mixed.csv': ('transaction_timestamp,amount,category,transaction_type,merchant,is_recurring\n'
            '2026-10-19T12:00:00+03:00,125.50,food,expense,Synthetic shop,false\n'
            '2026-10-19T13:00:00+03:00,75.25,transport,expense,Synthetic bus,false\n'
            '2026-10-19T12:00:00+03:00,125.50,food,expense,Synthetic shop,false\n'
            '2026-10-19T14:00:00+03:00,invalid,food,expense,Synthetic invalid,false\n'),
        'spendly-invalid.csv': 'wrong,columns\nsynthetic,only\n',
    }
    completed = set()
    deadline = time.monotonic() + 420
    try:
        adb('shell', 'mkdir', '-p', '/sdcard/Download')
        with tempfile.TemporaryDirectory(prefix='spendly-csv-lab-') as directory:
            for name, contents in fixtures.items():
                path = Path(directory) / name
                path.write_text(contents, encoding='utf-8')
                adb('push', str(path), '/sdcard/Download/' + name)
                adb('shell', 'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE',
                    '-d', 'file:///sdcard/Download/' + name)
        while time.monotonic() < deadline:
            text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
            if 'Some tests failed.' in text:
                raise RuntimeError('Native test failed; inspect its synthetic log.')
            for phase in re.findall(r'SPENDLY_PICKER:(cancel|mixed|repeat|invalid|recover)', text):
                if phase in completed:
                    continue
                if phase == 'cancel':
                    # Wait for the actual external picker before pressing Back.
                    if not any('documentsui' in n.get('package', '') for n in nodes()):
                        continue
                    adb('shell', 'input', 'keyevent', 'KEYCODE_BACK')
                else:
                    choose('spendly-invalid.csv' if phase == 'invalid' else 'spendly-mixed.csv')
                completed.add(phase)
                print('CSV_LAB:' + phase + ':completed', flush=True)
            if 'SPENDLY_NATIVE_IMPORT:passed' in text:
                assert len(completed) == 5
                return
            time.sleep(0.5)
        raise RuntimeError('Native CSV lab timed out.')
    finally:
        # These paths are fixed fictional fixtures on this explicitly disposable AVD.
        adb('shell', 'rm', '-f', '/sdcard/Download/spendly-mixed.csv',
            '/sdcard/Download/spendly-invalid.csv', '/sdcard/spendly-picker-ui.xml')


if __name__ == '__main__':
    main()
