"""Host side of the explicitly disposable emulator SMS acceptance test.

Never point this script at a physical device. Only fictional fixtures are used.
Run after starting backend.scripts.run_sms_acceptance_backend and before the
guarded Flutter integration target. Leaves app data for explicit process tests.
"""
import json
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ADB = Path.home() / "AppData/Local/Android/sdk/platform-tools/adb.exe"
SERIAL = "emulator-5580"
PACKAGE = "com.evagh.capstone.spending_support.acceptance"
BASE = "http://127.0.0.1:5057/api/v1"


def adb(*args, check=True):
    result = subprocess.run([str(ADB), "-s", SERIAL, *args], capture_output=True, text=True, timeout=25)
    if check and result.returncode:
        raise RuntimeError("Disposable emulator command failed: " + result.stderr[:150])
    return result.stdout


def request(path, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.load(response)["data"]


def sms(number):
    contents = {
        1: "Ksh214.25 sent to Example Person 0700000001 on 11/10/26 at 4:10 PM. Transaction cost, Ksh8.50.",
        2: "You bought Ksh75.00 of airtime on 12/10/26 at 5:53 PM. Transaction cost, Ksh0.00.",
        3: "You have received Ksh2,345.60 from Fictional Sender 0700***002 on 13/10/26 at 7:39 PM.",
    }
    content = contents.get(number, f"Ksh{350 + number}.00 paid to Fictional shop {number} on 22/10/26 at 8:{number:02d} PM. Transaction cost, Ksh0.00.")
    message = f"LABS{number:06d} Confirmed.{content} New M-PESA balance is Ksh9,876.54."
    output = adb("emu", "sms", "send", "MPESA", message)
    if "OK" not in output:
        raise RuntimeError("Emulator did not acknowledge synthetic SMS injection.")


def allow_contextual_permission():
    for _ in range(60):
        package = adb("shell", "dumpsys", "package", PACKAGE)
        if all(f"android.permission.{permission}: granted=true" in package for permission in ("READ_SMS", "RECEIVE_SMS")):
            return
        adb("shell", "uiautomator", "dump", "/sdcard/spendly-sms-lab-ui.xml", check=False)
        raw = adb("shell", "cat", "/sdcard/spendly-sms-lab-ui.xml", check=False)
        try:
            nodes = ET.fromstring(raw).iter("node")
            for node in nodes:
                if node.get("resource-id") == "android:id/aerr_wait":
                    import re
                    x1, y1, x2, y2 = map(int, re.findall(r"\d+", node.get("bounds")))
                    adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
                    print("SMS_LAB:waited_for_emulator_system_ui", flush=True)
                    break
                if node.get("package") == "com.google.android.permissioncontroller" and node.get("text", "").lower() == "allow":
                    import re
                    x1, y1, x2, y2 = map(int, re.findall(r"\d+", node.get("bounds")))
                    adb("shell", "input", "tap", str((x1 + x2) // 2), str((y1 + y2) // 2))
                    return
        except ET.ParseError:
            pass
        time.sleep(1)
    raise RuntimeError("Contextual SMS permission dialog was not shown.")


def assert_disposable_emulator():
    if not SERIAL.startswith("emulator-") or adb("shell", "getprop", "ro.hardware").strip() not in {"ranchu", "goldfish"}:
        raise RuntimeError("Only the new disposable emulator is allowed.")
    name = adb("emu", "avd", "name").splitlines()[0].strip()
    if name not in {"SpendlySmsLab_20261022", "SpendlySmsLifecycle_20261022", "SpendlySmsFinal_20261023"}:
        raise RuntimeError("This is not the named Spendly disposable SMS emulator.")


def main():
    assert_disposable_emulator()
    target = request("/sms-acceptance-target")
    if target.get("database") != "in_memory" or target.get("disposable") is not True:
        raise RuntimeError("Disposable backend guard failed.")
    completed = set()
    for _ in range(1000):
        phase = request("/sms-lab-checkpoint")["phase"]
        if phase in completed or phase == "waiting":
            time.sleep(1)
            continue
        print("SMS_LAB_PHASE:" + phase, flush=True)
        if phase == "seed_history":
            for number in (1, 2, 3):
                sms(number)
        elif phase == "permission":
            allow_contextual_permission()
        elif phase == "background":
            adb("shell", "input", "keyevent", "KEYCODE_HOME")
            sms(4)
            time.sleep(2)
        elif phase in {"offline", "pending_logout"}:
            adb("reverse", "--remove", "tcp:5057")
            try:
                sms(5 if phase == "offline" else 7)
                request("/sms-lab-checkpoint", {"ack": True})
                # Control uses the emulator host alias, independently of the
                # data transport being interrupted. Wait for observed queueing
                # (and logout, where applicable), never a guessed SMS delay.
                for _ in range(60):
                    if request("/sms-lab-checkpoint")["phase"] != phase:
                        break
                    time.sleep(1)
                else:
                    raise RuntimeError("App did not complete the offline phase.")
            finally:
                adb("reverse", "tcp:5057", "tcp:5057")
            completed.add(phase)
            continue
        elif phase in {"reconnect", "after_logout", "duplicate"}:
            if phase == "duplicate":
                sms(5)
                time.sleep(1)
        elif phase == "foreground":
            adb("shell", "am", "start", "-n", PACKAGE + "/com.evagh.capstone.spending_support.MainActivity")
        elif phase == "off_delivery":
            sms(6)
            time.sleep(3)
        elif phase == "beta_delivery":
            sms(8)
            time.sleep(3)
        elif phase == "complete":
            request("/sms-lab-checkpoint", {"ack": True})
            print("SMS_LAB:completed", flush=True)
            return
        else:
            raise RuntimeError("Unknown lab checkpoint")
        completed.add(phase)
        request("/sms-lab-checkpoint", {"ack": True})
    raise RuntimeError("Lab timed out.")


if __name__ == "__main__":
    main()
